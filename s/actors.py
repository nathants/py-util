from __future__ import print_function, absolute_import
# import zmq.eventloop
# zmq.eventloop.ioloop.install()

# import s.sock
import s.hacks
import s.func

import tornado
import tornado.gen
import tornado.ioloop
import tornado.concurrent
import functools
import toro


class _Self(object):
    pass
    # def __init__(self):
    #     self._route = s.sock.route()
    #     self._sock = s.sock.bind('pull', self._route)
    #     self._sock.__enter__()

    # def __call__(self):
    #     return self._route

    # def recv(self):
    #     return self._sock.recv()

    # def send(self, route, msg):
    #     return s.sock.push(route, msg)


class _QueueSelf(object):
    def __init__(self):
        self._route = toro.Queue(100)

    def __call__(self):
        return self._route

    def recv(self):
        return self._route.get()

    def send(self, route, msg):
        return route.put(msg)


class _SelectiveSelf(object):
    def __init__(self, cls):
        self._self = cls()
        self._route = self._self._route

        self._to_redeliver = []
        self._redelivered = []
        self._try_redeliver = False
        self._last_msg = None

    def __call__(self):
        return self._route

    def send(self, *a, **kw):
        return self._self.send(*a, **kw)

    def recv(self):
        if self._redelivered and not self._to_redeliver:
            self._to_redeliver = self._redelivered[:]
            self._redelivered = []
            self._try_redeliver = False
        if self._to_redeliver and self._try_redeliver:
            future = tornado.concurrent.Future()
            future.set_result(self._to_redeliver.pop(0))
            return future
        else:
            future = self._self.recv()
            def fn(f):
                self._last_msg = f.result()
                self._try_redeliver = True
            future.add_done_callback(fn)
            return future

    def requeue(self):
        if self._try_redeliver:
            self._redelivered.append(self._last_msg)
        else:
            self._to_redeliver.append(self._last_msg)


# TODO offer toro.Queue instead of zeromq. does it actually make a measureable difference? trongo?
@s.func.optionally_parameterized_decorator
def actor(ipc=True, selective_receive=False):
    def decorator(fn):
        @functools.wraps(fn)
        def _actor(*a, **kw):
            cls = _Self if ipc else _QueueSelf
            self = _SelectiveSelf(cls) if selective_receive else cls()
            tornado.gen.coroutine(fn)(self, *a, **kw)
            # TODO add on_done and on_error to the actors future to monitor its death
            return self._route
        return _actor
    return decorator
