from __future__ import absolute_import, print_function
import multiprocessing
import concurrent.futures
import logging
import s


_size = multiprocessing.cpu_count() + 2


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


submit = _submit_factory(concurrent.futures.ProcessPoolExecutor, globals())


new = _new_factory(multiprocessing.Process)


wait = _wait_factory(multiprocessing.Process)
