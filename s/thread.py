from __future__ import absolute_import, print_function
import threading
import s
import logging
import concurrent.futures


_size = 20


@s.cached.func
def _pool():
    logging.debug('new thread pool, size: %s', _size)
    return concurrent.futures.ThreadPoolExecutor(_size)


def new(fn, *a, **kw):
    daemon = kw.pop('_daemon', True)
    obj = threading.Thread(target=fn, args=a, kwargs=kw)
    obj.daemon = daemon
    obj.start()
    return obj


def submit(fn, *a, **kw):
    return _pool().submit(fn, *a, **kw)
