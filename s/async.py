from __future__ import print_function, absolute_import
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
                if isinstance(e, (tornado.gen.Return,) + ignore):
                    logging.debug('not logging exception "%s" in: %s', e, s.func.name(fn))
                else:
                    logging.exception('exception in: %s', s.func.name(fn))
    return fn


@s.hacks.optionally_parameterized_decorator
def coroutine(*ignore_exceptions, **coroutine_kw):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*a, **kw):
            if coroutine_kw.get('immutalize', True):
                a, kw = s.data.immutalize(a), s.data.immutalize(kw)
                trace_fn = s.trace.glue(fn)
            else:
                trace_fn = s.trace.bad_func(fn)
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


Return = tornado.gen.Return
moment = tornado.gen.moment
ioloop = tornado.ioloop.IOLoop.current
run_sync = ioloop().run_sync
Future = tornado.concurrent.Future
