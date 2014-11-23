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
        lambda: s.sock.connect('push', route).send_string('')
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
        sock = AsyncSock(sock)
    return sock


# TODO calls to bind and connection should cache socket objects. only new creates new sockets every time, and should be used with "with"


bind = functools.partial(new, 'bind')


connect = functools.partial(new, 'connect')


# TODO drop all the _string methods from Sock and AsyncSock, they should always decode utf-8
# need to *attempt* to encode and decode all parts of the message
# failure will happen, because of the routing binaries inserted by router/dealer and friends
# send(maybe_encode(msg))
# recv(maybe_decode(msg))


class AsyncSock(object):
    def __init__(self, sock):
        self._stream = zmq.eventloop.zmqstream.ZMQStream(sock)

    def recv_string(self, *a, **kw):
        return self._recv(lambda x: x[0].decode('utf-8'), *a, **kw)

    def recv_json(self, *a, **kw):
        return self._recv(lambda x: json.loads(x[0].decode('utf-8')), *a, **kw)

    def recv_multipart(self, *a, **kw):
        return self._recv(lambda x: x, *a, **kw)

    def recv_multipart_string(self, *a, **kw):
        return self._recv(lambda x: [y.decode('utf-8') for y in x], *a, **kw)

    def on_recv(self, fn):
        self._stream.on_recv(fn)

    def on_send(self, fn):
        self._stream.on_send(fn)

    def stop_on_send(self):
        self._stream.stop_on_send()

    def stop_on_recv(self):
        self._stream.stop_on_recv()

    def _recv(self, transform, *a, **kw):
        future = s.async.Future()
        def fn(msg):
            self._stream.stop_on_send()
            future.set_result(transform(msg))
        self._stream.on_recv(fn)
        return future

    def _action(method_name):
        def fn(self, *a, **kw):
            future = s.async.Future()
            def fn(*a):
                future.set_result(None)
            kw['callback'] = fn
            getattr(self._stream, method_name)(*a, **kw)
            return future
        return fn

    for name in ['send',
                 'send_string',
                 'send_multipart',
                 'send_multipart_string',
                 'send_json']:
        locals()[name] = _action(name)


_devices = {
    'forwarder': ['sub', 'pub'],
    'queue': ['router', 'dealer'],
    'streamer': ['pull', 'push'],
}


def device(kind, in_route, out_route, **kw):
    in_kind, out_kind = _devices[kind.lower()]
    in_sock = bind(in_kind, in_route, **kw)
    out_sock = bind(out_kind, out_route, **kw)
    return zmq.device(getattr(zmq, kind.upper()), in_sock, out_sock)
    return zmq.device(getattr(zmq, kind.upper()), in_sock, out_sock)


# TODO open a pr to pyzmq for these inconsistencies and stop monkey patching it


def _send_multipart_string_stream(self, parts, flags=0, copy=True, encoding='utf-8', callback=None):
    return self.send_multipart([x.encode(encoding) for x in parts], flags=flags, copy=copy, callback=callback)


def _send_multipart_string(self, parts, flags=0, copy=True, encoding='utf-8'):
    return self.send_multipart([x.encode(encoding) for x in parts], flags=flags, copy=copy)


def _recv_multipart_string(self, flags=0, encoding='utf-8'):
    return [x.decode(encoding) for x in self.recv_multipart(flags=flags)]


def _enter(self):
    return self


def _exit(self, *a, **kw):
    self.close()


zmq.sugar.Socket.send_multipart_string = _send_multipart_string
zmq.sugar.Socket.recv_multipart_string = _recv_multipart_string
zmq.eventloop.zmqstream.ZMQStream.send_multipart_string = _send_multipart_string_stream
zmq.eventloop.zmqstream.ZMQStream.recv_multipart_string = _recv_multipart_string
zmq.eventloop.zmqstream.ZMQStream.__enter__ = _enter
zmq.eventloop.zmqstream.ZMQStream.__exit__ = _exit
