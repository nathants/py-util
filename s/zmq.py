from __future__ import print_function, absolute_import
import zmq.eventloop
zmq.eventloop.ioloop.install()

import zmq
import zmq.eventloop.zmqstream
import tornado.ioloop
import logging


def ioloop():
    return tornado.ioloop.IOLoop.current()


def _split(arg):
    try:
        kind, action, route = arg.split()
    except ValueError:
        kind = arg
        action = route = None
    return kind, action, route


def socket(arg, subscriptions=[""], sockopts={}):
    assert isinstance(subscriptions, (list, tuple)), 'subscriptions not a list: {}'.format(subscriptions)
    kind, action, route = _split(arg)
    sock = zmq.Context().socket(getattr(zmq, kind)) # we should not recreate contexts in the same thread, only in diff procs
    for k, v in sockopts.items():
        setattr(sock, k, v)
    if route:
        logging.debug('[zmq]', kind, action, route)
        getattr(sock, action)(route)
    if kind == 'SUB' and subscriptions:
        for subscr in subscriptions:
            logging.debug('[subscribe]', '"{}"'.format(subscr))
            sock.setsockopt(zmq.SUBSCRIBE, subscr)
    return sock


def stream(arg, subscriptions=[""], sockopts={}):
    sock = socket(arg, subscriptions, sockopts)
    return zmq.eventloop.zmqstream.ZMQStream(sock)


_devices = {
    'FORWARDER': ['SUB', 'PUB'],
    'QUEUE': ['ROUTER', 'DEALER'],
    'STREAMER': ['PULL', 'PUSH'],
}


def device(arg):
    kind, proto, in_port, out_port = arg.split()
    in_kind, out_kind = _devices[kind]
    in_sock = socket('{in_kind} bind {proto}://0.0.0.0:{in_port}'.format(**locals()))
    out_sock = socket('{out_kind} bind {proto}://0.0.0.0:{out_port}'.format(**locals()))
    logging.debug('[zmq-device]', kind, proto, in_port, '->', out_port)
    return zmq.device(getattr(zmq, kind), in_sock, out_sock)
