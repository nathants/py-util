from __future__ import absolute_import, print_function
import multiprocessing
import concurrent.futures
import logging
import s


_size = multiprocessing.cpu_count() + 2


@s.cached.func
def _pool():
    logging.debug('new process pool, size: %s', _size)
    return concurrent.futures.ProcessPoolExecutor(_size)


def shutdown_pool():
    _pool().shutdown(wait=False)
    _pool.clear_cache()


def new(fn, *a, **kw):
    daemon = kw.pop('_daemon', True)
    obj = multiprocessing.Process(target=fn, args=a, kwargs=kw)
    obj.daemon = daemon
    obj.start()
    return obj


def wait(*fns):
    objs = [new(fn) for fn in fns]
    [obj.join() for obj in objs]


def submit(fn, *a, **kw):
    return _pool().submit(fn, *a, **kw)
