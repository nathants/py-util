from __future__ import print_function, absolute_import
import zmq.eventloop
zmq.eventloop.ioloop.install()

import zmq
import zmq.eventloop.zmqstream
import tornado.ioloop
import zmq.sugar


def ioloop():
    return tornado.ioloop.IOLoop.current()


def _split(arg):
    kind, action, route = arg.split()
    assert kind in ['PUB', 'SUB', 'REQ', 'REP', 'PUSH', 'PULL', 'ROUTER', 'DEALER', 'PAIR'], 'invalid kind: {}'.format(kind)
    assert action in ['bind', 'connect'], 'invalid action: {}'.format(action)
    assert route.split('://')[0] in ['ipc', 'tcp', 'pgm', 'epgm'], 'invalid route: {}'.format(route)
    return kind, action, route


def socket(arg, subscriptions=[""], sockopts={}, stream=False, timeout=None, snd_hwm=1, rcv_hwm=1):
    kind, action, route = _split(arg)
    sock = zmq.Context().socket(getattr(zmq, kind)) # we should not recreate contexts in the same thread, only in diff procs
    for k, v in sockopts.items():
        setattr(sock, k, v)
    getattr(sock, action)(route)
    if kind == 'SUB':
        assert isinstance(subscriptions, (list, tuple)), 'subscriptions not a list: {}'.format(subscriptions)
        for subscr in subscriptions:
            sock.setsockopt(zmq.SUBSCRIBE, subscr.encode('utf-8'))
    if timeout:
        sock.setsockopt(zmq.LINGER, timeout)
        sock.setsockopt(zmq.SNDTIMEO, timeout)
        sock.setsockopt(zmq.RCVTIMEO, timeout)
    sock.setsockopt(zmq.SNDHWM, snd_hwm)
    sock.setsockopt(zmq.RCVHWM, rcv_hwm)
    if stream:
        sock = zmq.eventloop.zmqstream.ZMQStream(sock)
    return sock


_devices = {
    'FORWARDER': ['SUB', 'PUB'],
    'QUEUE': ['ROUTER', 'DEALER'],
    'STREAMER': ['PULL', 'PUSH'],
}


def device(arg):
    kind, in_route, out_route = arg.split()
    in_kind, out_kind = _devices[kind]
    in_sock = socket('{in_kind} bind {in_route}'.format(**locals()))
    out_sock = socket('{out_kind} bind {out_route}'.format(**locals()))
    return zmq.device(getattr(zmq, kind), in_sock, out_sock)


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
zmq.eventloop.zmqstream.ZMQStream.send_multipart_string = _send_multipart_string
zmq.eventloop.zmqstream.ZMQStream.recv_multipart_string = _recv_multipart_string
zmq.eventloop.zmqstream.ZMQStream.__enter__ = _enter
zmq.eventloop.zmqstream.ZMQStream.__exit__ = _exit
