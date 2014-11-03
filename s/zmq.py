from __future__ import print_function, absolute_import
import zmq.eventloop
zmq.eventloop.ioloop.install()

import zmq
import zmq.eventloop.zmqstream
import tornado.ioloop
import zmq.sugar


def ioloop():
    return tornado.ioloop.IOLoop.current()


def socket(kind, action, route, subscriptions=[""], sockopts={}, async=False, timeout=None, hwm=1):
    assert kind in ['PUB', 'SUB', 'REQ', 'REP', 'PUSH', 'PULL', 'ROUTER', 'DEALER', 'PAIR'], 'invalid kind: {}'.format(kind)
    assert action in ['bind', 'connect'], 'invalid action: {}'.format(action)
    assert route.split('://')[0] in ['ipc', 'tcp', 'pgm', 'epgm'], 'invalid route: {}'.format(route)
    sock = zmq.Context().socket(getattr(zmq, kind)) # we should not recreate contexts in the same thread, only in diff procs
    for k, v in sockopts.items():
        setattr(sock, k, v)
    try:
        getattr(sock, action)(route)
    except:
        print(kind, action, route)
        raise
    if kind == 'SUB':
        assert isinstance(subscriptions, (list, tuple)), 'subscriptions not a list: {}'.format(subscriptions)
        for subscr in subscriptions:
            sock.setsockopt(zmq.SUBSCRIBE, subscr.encode('utf-8'))
    if timeout:
        sock.setsockopt(zmq.SNDTIMEO, timeout)
        sock.setsockopt(zmq.RCVTIMEO, timeout)
    sock.setsockopt(zmq.SNDHWM, hwm)
    sock.setsockopt(zmq.RCVHWM, hwm)
    if async:
        sock = zmq.eventloop.zmqstream.ZMQStream(sock)
    return sock


_devices = {
    'FORWARDER': ['SUB', 'PUB'],
    'QUEUE': ['ROUTER', 'DEALER'],
    'STREAMER': ['PULL', 'PUSH'],
}


def device(kind, in_route, out_route, **kw):
    in_kind, out_kind = _devices[kind]
    in_sock = socket(in_kind, 'bind', in_route, **kw)
    out_sock = socket(out_kind, 'bind', out_route, **kw)
    return zmq.device(getattr(zmq, kind), in_sock, out_sock)
    return zmq.device(getattr(zmq, kind), in_sock, out_sock)


def _send_multipart_string(self, parts, flags=0, copy=True, encoding='utf-8'):
    return self.send_multipart([x.encode(encoding) for x in parts], flags=flags, copy=copy)


def _recv_multipart_string(self, flags=0, encoding='utf-8'):
    return [x.decode(encoding) for x in self.recv_multipart(flags=flags)]


def _enter(self):
    return self


def _exit(self, *a, **kw):
    self.close()


# TODO open a pr to pyzmq for these inconsistencies and stop monkey patching it
zmq.sugar.Socket.send_multipart_string = _send_multipart_string
zmq.sugar.Socket.recv_multipart_string = _recv_multipart_string
zmq.eventloop.zmqstream.ZMQStream.send_multipart_string = _send_multipart_string
zmq.eventloop.zmqstream.ZMQStream.recv_multipart_string = _recv_multipart_string
zmq.eventloop.zmqstream.ZMQStream.__enter__ = _enter
zmq.eventloop.zmqstream.ZMQStream.__exit__ = _exit
