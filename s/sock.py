from __future__ import print_function, absolute_import
import zmq.eventloop
zmq.eventloop.ioloop.install()

import s
import json
import functools
import zmq
import zmq.eventloop.zmqstream
import zmq.sugar
import uuid
import os
import datetime


def timeout(seconds):
    r = route()
    s.async.ioloop().add_timeout(
        datetime.timedelta(seconds=seconds),
        lambda: s.sock.push(r, '')
    )
    return s.sock.bind('pull', r)


def route():
    while True:
        route = '/tmp/{}'.format(uuid.uuid4())
        if not os.path.isfile(route):
            return 'ipc://' + route


@s.cached.memoize
def context(pid):
    return zmq.Context()


def new(action, kind, route, subscriptions=[""], sockopts={}, hwm=1):
    assert kind.lower() in ['pub', 'sub', 'req', 'rep', 'push', 'pull', 'router', 'dealer', 'pair'], 'invalid kind: {}'.format(kind)
    assert action in ['bind', 'connect'], 'invalid action: {}'.format(action)
    assert route.split('://')[0] in ['ipc', 'tcp', 'pgm', 'epgm'], 'invalid route: {}'.format(route)
    sock = context(os.getpid()).socket(getattr(zmq, kind.upper()))
    sock.hwm = hwm
    for k, v in sockopts.items():
        setattr(sock, k, v)
    getattr(sock, action)(route) # sock.bind(route)
    _setup_subscriptions(sock, kind, subscriptions)
    return AsyncSock(sock)


def _setup_subscriptions(sock, kind, subscriptions):
    if kind.lower() == 'sub':
        assert isinstance(subscriptions, (list, tuple)), 'subscriptions not a list: {}'.format(subscriptions)
        for subscr in subscriptions:
            sock.setsockopt(zmq.SUBSCRIBE, subscr.encode('utf-8'))


bind = functools.partial(new, 'bind')
connect = functools.partial(new, 'connect')


_devices = {
    'forwarder': ['sub', 'pub'],
    'queue': ['router', 'dealer'],
    'streamer': ['pull', 'push'],
}


def device(kind, in_route, out_route, **kw):
    in_kind, out_kind = _devices[kind.lower()]
    in_sock = bind(in_kind, in_route, **kw)._sock.socket
    out_sock = bind(out_kind, out_route, **kw)._sock.socket
    return zmq.device(getattr(zmq, kind.upper()), in_sock, out_sock)


def process_recv(msg):
    msg = msg.decode('utf-8')
    msg = json.loads(msg)
    msg = s.data.freeze(msg)
    return msg


def process_send(msg):
    msg = json.dumps(msg)
    msg = msg.encode('utf-8')
    return msg


class AsyncSock(object):
    def __init__(self, sock):
        self._sock = zmq.eventloop.zmqstream.ZMQStream(sock)
        self.entered = False

    def __enter__(self, *a, **kw):
        self.entered = True
        return self

    def __exit__(self, *a, **kw):
        self._sock.close()

    def type(self):
        return self._sock.socket.type

    def recv(self, timeout=None):
        assert s.async.ioloop().started, 'you are using async recv, but an ioloop hasnt been started'
        assert self.entered, 'you must use sockets as context managers, so that they are closed at some point'
        assert not self._sock._recv_callback, 'there is already a recv callback registered'
        future = s.async.Future()
        future._action = 'recv()'
        def cb(msg):
            self._sock.stop_on_recv()
            if self.type() == zmq.SUB:
                topic, msg = msg
                msg = process_recv(msg)
                topic = topic.decode('utf-8')
                msg = topic, msg
                future.set_result(msg)
            elif self.type() in [zmq.ROUTER, zmq.DEALER]:
                identities, msg = msg[:-1], msg[-1]
                msg = process_recv(msg)
                msg = tuple(identities + [msg])
                future.set_result(msg)
            else:
                [msg] = msg
                msg = process_recv(msg)
                future.set_result(msg)
        if timeout:
            def timeout_cb():
                self._sock.stop_on_recv()
                future.set_exception(Timeout)
            t = s.async.ioloop().add_timeout(datetime.timedelta(seconds=timeout), timeout_cb)
            future.add_done_callback(lambda _: s.async.ioloop().remove_timeout(t))
        self._sock.on_recv(cb)
        return future

    def send(self, msg, topic='', timeout=None):
        assert not topic or self.type() == zmq.PUB, 'you can only use kwarg topic with pub sockets'
        assert s.async.ioloop().started, 'you are using async send, but an ioloop hasnt been started'
        assert self.entered, 'you must use sockets as context managers, so that they are closed at some point'
        assert msg is not None, 'you cannot use None as a message'
        future = s.async.Future()
        future._action = 'send({}{})'.format(msg, ', topic={}'.format(topic) if topic else '')
        def fn(*_):
            self._sock.stop_on_send()
            future.set_result(None)
        if self.type() == zmq.PUB:
            msg = process_send(msg)
            topic = topic.encode('utf-8')
            msg = topic, msg
            self._sock.send_multipart(msg, callback=fn)
        elif self.type() in [zmq.ROUTER, zmq.DEALER]:
            identities, msg = msg[:-1], msg[-1]
            msg = process_send(msg)
            msg = identities + (msg,)
            self._sock.send_multipart(msg, callback=fn)
        else:
            msg = process_send(msg)
            self._sock.send(msg, callback=fn)
        if timeout:
            def cb():
                q = self._sock._send_queue
                vals = []
                while not q.empty():
                    vals.append(q.get())
                for val in vals:
                    if val[0] != (msg if isinstance(msg, type) else [msg]):
                        q.put(val)
                future.set_exception(Timeout)
            t = s.async.ioloop().add_timeout(datetime.timedelta(seconds=timeout), cb)
            future.add_done_callback(lambda _: s.async.ioloop().remove_timeout(t))
        return future


class Timeout(Exception):
    pass


def select(*socks):
    future = s.async.Future()
    def fn(sock, msg):
        for x in socks:
            x._sock.stop_on_recv()
        if sock.type() == zmq.SUB:
            topic, msg = msg
            topic = topic.decode('utf-8')
            msg = process_recv(msg)
            future.set_result([id(sock), [topic, msg]])
        else:
            [msg] = msg
            msg = process_recv(msg)
            future.set_result([id(sock), msg])
    for sock in socks:
        sock._sock.on_recv(functools.partial(fn, sock))
    return future


@s.async.coroutine(AssertionError)
def open_use_close(kind, method, route, msg=None, subscriptions=None, timeout=None):
    kw = {'subscriptions': subscriptions} if subscriptions else {}
    with connect(kind, route, **kw) as sock:
        if method == 'send':
            val = yield sock.send(msg, timeout=timeout)
        elif method == 'recv':
            val = yield sock.recv(timeout=timeout)
        else:
            raise AssertionError('bad method: {method}'.format(**locals()))
    raise s.async.Return(val)


def _make_sync(fn):
    def fn_sync(route, msg=None, subscriptions=None):
        @s.async.coroutine
        def main():
            if msg is not None:
                yield fn(route, msg)
            else:
                if subscriptions:
                    val = yield fn(route, subscriptions=subscriptions)
                else:
                    val = yield fn(route)
                raise s.async.Return(val)
        return s.async.run_sync(main)
    return fn_sync


push = functools.partial(open_use_close, 'push', 'send')
pull = functools.partial(open_use_close, 'pull', 'recv')
sub = functools.partial(open_use_close, 'sub', 'recv')
pull_sync = _make_sync(pull)
push_sync = _make_sync(push)
sub_sync = _make_sync(sub)
