from __future__ import print_function, absolute_import
import zmq.eventloop
zmq.eventloop.ioloop.install()

import s
import json
import functools
import zmq
import zmq.eventloop.zmqstream
import tornado.ioloop
import zmq.sugar
import uuid
import os
import datetime


def timeout(seconds):
    route = new_ipc_route()
    ioloop().add_timeout(
        datetime.timedelta(seconds=seconds),
        lambda: s.sock.connect('push', route).send('')
    )
    return s.sock.bind('pull', route)


def select(*socks):
    future = s.async.Future()
    def fn(sock, msg):
        for x in socks:
            x.stop_on_recv()
        future.set_result([id(sock), msg])
    for sock in socks:
        sock.on_recv(functools.partial(fn, sock))
    return future


def ioloop():
    return tornado.ioloop.IOLoop.current()


def new_ipc_route():
    while True:
        route = '/tmp/{}'.format(uuid.uuid4())
        if not os.path.isfile(route):
            return 'ipc://' + route


def new(action, kind, route, subscriptions=[""], sockopts={}, async=True, timeout=None, hwm=1):
    assert kind.lower() in ['pub', 'sub', 'req', 'rep', 'push', 'pull', 'router', 'dealer', 'pair'], 'invalid kind: {}'.format(kind)
    assert action in ['bind', 'connect'], 'invalid action: {}'.format(action)
    assert route.split('://')[0] in ['ipc', 'tcp', 'pgm', 'epgm'], 'invalid route: {}'.format(route)
    sock = zmq.Context().socket(getattr(zmq, kind.upper())) # we should not recreate contexts in the same thread, only in diff procs
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
    if async:
        return AsyncSock(sock)
    else:
        return Sock(sock)


# TODO calls to bind and connection should cache socket objects. only new creates new sockets every time, and should be used with "with"


bind = functools.partial(new, 'bind')


connect = functools.partial(new, 'connect')


_devices = {
    'forwarder': ['sub', 'pub'],
    'queue': ['router', 'dealer'],
    'streamer': ['pull', 'push'],
}


def device(kind, in_route, out_route, **kw):
    in_kind, out_kind = _devices[kind.lower()]
    in_sock = bind(in_kind, in_route, **kw)
    out_sock = bind(out_kind, out_route, **kw)
    return zmq.device(getattr(zmq, kind.upper()), in_sock._sock, out_sock._sock)


maybe_encode = s.func.try_fn(lambda x: x.encode('utf-8'))
maybe_decode = s.func.try_fn(lambda x: x.decode('utf-8'))


class Sock(object):
    def __init__(self, sock):
        self._sock = sock

    def __enter__(self, *a, **kw):
        return self

    def __exit__(self, *a, **kw):
        self._sock.close()

    def _recv(method_name):
        def fn(self, *a, **kw):
            msg = getattr(self._sock, method_name)(*a, **kw)
            if isinstance(msg, (list, tuple)):
                return [maybe_decode(x) for x in msg]
            else:
                return maybe_decode(msg)
        return fn

    for name in ['recv',
                 'recv_multipart',
                 'recv_json']:
        locals()[name] = _recv(name)

    def _send(method_name):
        def fn(self, msg, *a, **kw):
            if isinstance(msg, (list, tuple)):
                msg = [maybe_encode(x) for x in msg]
            else:
                msg = maybe_encode(msg)
            return getattr(self._sock, method_name)(msg, *a, **kw)
        return fn

    for name in ['send',
                 'send_multipart',
                 'send_json']:
        locals()[name] = _send(name)


class AsyncSock(object):
    def __init__(self, sock):
        self._sock = zmq.eventloop.zmqstream.ZMQStream(sock)

    def __enter__(self, *a, **kw):
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

    def _recv(transform):
        def fn(self):
            future = s.async.Future()
            def cb(msg):
                self._sock.stop_on_recv()
                msg = [maybe_decode(x) for x in msg]
                msg = transform(msg)
                future.set_result(msg)
            self._sock.on_recv(cb)
            return future
        return fn

    for name, fn in [('recv', lambda x: x[0]),
                     ('recv_json', lambda x: json.loads(x[0])),
                     ('recv_multipart', lambda x: x)]:
        locals()[name] = _recv(fn)

    def _send(method_name):
        def fn(self, msg, *a, **kw):
            future = s.async.Future()
            def fn(*_):
                self.stop_on_send()
                future.set_result(None)
            kw['callback'] = fn
            if isinstance(msg, (list, tuple)):
                msg = [maybe_encode(x) for x in msg]
            else:
                msg = maybe_encode(msg)
            getattr(self._sock, method_name)(msg, *a, **kw)
            return future
        return fn

    for name in ['send',
                 'send_multipart',
                 'send_json']:
        locals()[name] = _send(name)
