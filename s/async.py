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
                if not isinstance(e, (tornado.gen.Return,) + ignore):
                    _recent.append(e)
                    logging.exception('exception in %s', future._name)
    return fn


@s.hacks.optionally_parameterized_decorator
def coroutine(*ignore_exceptions, **coroutine_kw):
    def decorator(fn):
        assert inspect.isgeneratorfunction(fn), 'non generator cannot be a s.async.coroutine: {}'.format(s.func.name(fn))
        @functools.wraps(fn)
        def decorated(*a, **kw):
            if not coroutine_kw.get('trace', True):
                trace_fn = fn
            else:
                trace_fn = s.trace.trace(fn, coroutine_kw.get('freeze', True))
            future = tornado.gen.coroutine(trace_fn)(*a, **kw)
            future._name = s.func.name(fn)
            callback = _log_exceptions(*ignore_exceptions)
            ioloop().add_future(future, callback)
            return future
        decorated._is_coroutine = True
        return decorated
    return decorator


def sleep(duration_seconds):
    future = tornado.concurrent.Future()
    ioloop().add_timeout(
        datetime.timedelta(seconds=duration_seconds),
        lambda: future.set_result(None)
    )
    return future


class _IOLoop(object):
    def __init__(self, ioloop):
        self.ioloop = ioloop
        self.started = False

    def start(self):
        self.started = True
        self.ioloop.start()

    def __getattr__(self, k):
        return getattr(self.ioloop, k)


def ioloop_clear():
    ioloop.clear_cache()
    tornado.ioloop.IOLoop.clear_instance()


@s.cached.func
def ioloop():
    return _IOLoop(tornado.ioloop.IOLoop.instance())


def run_sync(fn, *a, **kw):
    timeout = kw.pop('timeout', None)
    io = ioloop()
    io.started = True
    val = io.run_sync(lambda: fn(*a, **kw), timeout=timeout)
    while io._callbacks:
        io._callbacks.pop()
    io.started = False
    return val


Return = tornado.gen.Return
moment = tornado.gen.moment
Future = tornado.concurrent.Future
chain = tornado.concurrent.chain_future


class _Self(object):
    def __init__(self):
        self._route = s.sock.route()
        self._sock = s.sock.bind('pull', self._route)
        self._sock.__enter__()

    def __call__(self):
        return self._route

    def recv(self):
        return self._sock.recv()


class _SelectiveSelf(_Self):
    def __init__(self):
        _Self.__init__(self)
        self._to_redeliver = []
        self._redelivered = []
        self._try_redeliver = False
        self._last_msg = None

    def recv(self):
        if self._redelivered and not self._to_redeliver:
            self._to_redeliver = self._redelivered[:]
            self._redelivered = []
            self._try_redeliver = False
        if self._to_redeliver and self._try_redeliver:
            future = Future()
            future.set_result(self._to_redeliver.pop(0))
            return future
        else:
            future = self._sock.recv()
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


# TODO not using push/pull instead of send/recv actually better?
# TODO offer toro.Queue instead of zeromq. does it actually make a measureable difference? trongo?
@s.hacks.optionally_parameterized_decorator
def actor(selective_receive=False):
    def decorator(fn):
        assert not getattr(fn, '_is_coroutine', False), 'actors should be normals funs, will be converted to coroutines: {}'.format(s.func.name(fn))
        @functools.wraps(fn)
        def _actor(*a, **kw):
            self = _SelectiveSelf() if selective_receive else _Self()
            coroutine(freeze=False)(fn)(self, *a, **kw)
            # TODO add on_done and on_error to the actors future to monitor its death
            return self._route
        return _actor
    return decorator


# TODO is this actually good? obfuscates?
def make_sync(fn):
    def fn_sync(*a, **kw):
        @s.async.coroutine
        def main():
            val = yield fn(*a, **kw)
            raise s.async.Return(val)
        return s.async.run_sync(main)
    return fn_sync
