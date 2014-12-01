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
    route = new_ipc_route()
    s.async.ioloop().add_timeout(
        datetime.timedelta(seconds=seconds),
        lambda: s.sock.push(route, '')
    )
    return s.sock.bind('pull', route)


def new_ipc_route():
    while True:
        route = '/tmp/{}'.format(uuid.uuid4())
        if not os.path.isfile(route):
            return 'ipc://' + route


def new(action, kind, route, subscriptions=[""], sockopts={}, timeout=None, hwm=1):
    assert kind.lower() in ['pub', 'sub', 'req', 'rep', 'push', 'pull', 'router', 'dealer', 'pair'], 'invalid kind: {}'.format(kind)
    assert action in ['bind', 'connect'], 'invalid action: {}'.format(action)
    assert route.split('://')[0] in ['ipc', 'tcp', 'pgm', 'epgm'], 'invalid route: {}'.format(route)
    sock = zmq.Context().socket(getattr(zmq, kind.upper())) # TODO we should not recreate contexts in the same thread, only in diff procs
    for k, v in sockopts.items():
        setattr(sock, k, v)
    try:
        getattr(sock, action)(route)
    except:
        raise
    if kind.lower() == 'sub':
        assert isinstance(subscriptions, (list, tuple)), 'subscriptions not a list: {}'.format(subscriptions)
        for subscr in subscriptions:
            sock.setsockopt(zmq.SUBSCRIBE, subscr.encode('utf-8'))
    if timeout:
        sock.setsockopt(zmq.SNDTIMEO, timeout)
        sock.setsockopt(zmq.RCVTIMEO, timeout)
    sock.setsockopt(zmq.SNDHWM, hwm)
    sock.setsockopt(zmq.RCVHWM, hwm)
    return AsyncSock(sock)


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

    def on_recv(self, fn):
        self._sock.on_recv(fn)

    def on_send(self, fn):
        self._sock.on_send(fn)

    def stop_on_send(self):
        self._sock.stop_on_send()

    def stop_on_recv(self):
        self._sock.stop_on_recv()

    def type(self):
        return self._sock.socket.type

    def recv(self):
        assert s.async.ioloop().started, 'you are using async recv, but an ioloop hasnt been started'
        assert self.entered, 'you must use sockets as context managers, so that they are closed at some point'
        assert not self._sock._recv_callback, 'there is already a recv callback registered'
        future = s.async.Future()
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
        self._sock.on_recv(cb)
        return future

    def send(self, msg, topic=''):
        assert not topic or self.type() == zmq.PUB, 'you can only use kwarg topic with pub sockets'
        assert s.async.ioloop().started, 'you are using async send, but an ioloop hasnt been started'
        assert self.entered, 'you must use sockets as context managers, so that they are closed at some point'
        assert msg is not None, 'you cannot use None as a message'
        future = s.async.Future()
        def fn(*_):
            self.stop_on_send()
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
        return future


def select(*socks):
    future = s.async.Future()
    def fn(sock, msg):
        for x in socks:
            x.stop_on_recv()
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
        sock.on_recv(functools.partial(fn, sock))
    return future


# TODO who takes args and kwargs. socket? push? timeout?
# TODO None is not a valid value

@s.async.coroutine(AssertionError)
def open_use_close(kind, method, route, msg=None, **kw):
    with connect(kind, route, **kw) as sock:
        if method == 'send':
            val = yield sock.send(msg)
        elif method == 'recv':
            val = yield sock.recv()
        else:
            raise AssertionError('bad method: {method}'.format(**locals()))
    raise s.async.Return(val)


push = functools.partial(open_use_close, 'push', 'send')
pull = functools.partial(open_use_close, 'pull', 'recv')
