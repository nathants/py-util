from __future__ import print_function, absolute_import
import zmq.eventloop
zmq.eventloop.ioloop.install()

import inspect
import s
import tornado
import tornado.gen
import tornado.ioloop
import tornado.concurrent
import collections
import logging
import functools
import datetime


_recent = collections.deque(maxlen=99)


def _log_exceptions(*ignore):
    def fn(future):
        try:
            future.result()
        except Exception as e:
            if e not in _recent:
                _recent.append(e)
                if not isinstance(e, (tornado.gen.Return,) + ignore):
                    logging.exception('exception in future: %s', future)
    return fn


@s.hacks.optionally_parameterized_decorator
def coroutine(*ignore_exceptions, **coroutine_kw):
    def decorator(fn):
        assert inspect.isgeneratorfunction(fn), 'non generator cannot be a s.async.coroutine: {}'.format(s.func.name(fn))
        @functools.wraps(fn)
        def decorated(*a, **kw):
            if not coroutine_kw.get('trace', True):
                trace_fn = fn
            elif coroutine_kw.get('freeze', True):
                trace_fn = s.trace.glue(fn)
            else:
                trace_fn = s.trace.mutable(fn)
            future = tornado.gen.coroutine(trace_fn)(*a, **kw)
            callback = _log_exceptions(*ignore_exceptions)
            tornado.ioloop.IOLoop.current().add_future(future, callback)
            return future
        decorated._is_coroutine = True
        return decorated
    return decorator


def sleep(duration_seconds):
    future = tornado.concurrent.Future()
    tornado.ioloop.IOLoop.current().add_timeout(
        datetime.timedelta(seconds=duration_seconds),
        lambda: future.set_result(None)
    )
    return future


class _IOLoop(object):
    def __init__(self):
        self.ioloop = tornado.ioloop.IOLoop.current()
        self.started = False

    def start(self):
        self.started = True
        self.ioloop.start()

    def clear(self):
        self.started = False

    def __getattr__(self, k):
        return getattr(self.ioloop, k)


@s.cached.func
def ioloop():
    return _IOLoop()


def run_sync(func, timeout=None):
    io = ioloop()
    io.started = True
    val = io.run_sync(func, timeout=timeout)
    while io._callbacks:
        io._callbacks.pop()
    io.started = False
    return val


Return = tornado.gen.Return
moment = tornado.gen.moment
Future = tornado.concurrent.Future


class _Self(object):
    def __init__(self, name):
        self._name = name
        self._route = s.sock.route()
        self._sock = s.sock.bind('pull', self._route)
        self._sock.__enter__()
        self._inbox = []
        self._parked_recv = None
        self._main()

    @s.async.coroutine(freeze=False)
    def _main(self):
        while True:
            msg = yield self._sock.recv()
            if self._parked_recv:
                self._parked_recv.set_result(msg)
                self._parked_recv = None
            else:
                self._inbox.append(msg)

    def __call__(self):
        return self._route

    def send(self, route, msg, **kw):
        return s.sock.push(route, msg, **kw)

    def recv(self):
        future = Future()
        if self._inbox:
            msg = self._inbox.pop()
            future.set_result(msg)
        else:
            self._parked_recv = future
        return future


def actor(fn):
    assert not getattr(fn, '_is_coroutine', False), 'actors should be normals funs, will be converted to coroutines: {}'.format(s.func.name(fn))
    @functools.wraps(fn)
    def _actor(*a, **kw):
        self = _Self(s.func.name(fn))
        coroutine(freeze=False)(fn)(self, *a, **kw)
        return self._route
    return _actor
