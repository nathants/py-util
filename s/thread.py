from __future__ import absolute_import, print_function
import threading
import concurrent.futures
import s
import logging


# todo better management of changing pool size mid program, and choosing whether to replace existing or create new pool


_size = 50


def _pool_factory():
    @s.cached.func
    def _pool(cls, size):
        logging.info('new:', cls, 'size:', size)
        return cls(size)
    return _pool


_pool = _pool_factory()


def _new_factory(cls):
    def _new(fn, *a, **kw):
        daemon = kw.pop('daemon', True)
        obj = cls(target=fn, args=a, kwargs=kw)
        obj.daemon = daemon
        obj.start()
        return obj
    return _new


def _wait_factory(cls):
    _new = _new_factory(cls)
    def _wait(*fns):
        objs = [_new(fn) for fn in fns]
        [obj.join() for obj in objs]
    return _wait


def _submit_factory(cls, _globals):
    def _submit(fn, *a, **kw):
        pool = _globals['_pool'](cls, _globals['_size'])
        return pool.submit(fn, *a, **kw)
    return _submit


# todo is this complected? just pass values instead of globals? benefit to globals?
submit = _submit_factory(concurrent.futures.ThreadPoolExecutor, globals())


new = _new_factory(threading.Thread)


wait = _wait_factory(threading.Thread)
