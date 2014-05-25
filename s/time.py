from __future__ import absolute_import
import contextlib
import time


@contextlib.contextmanager
def timer():
    val = {'seconds': None}
    start = time.time()
    try:
        yield val
    except:
        raise
    finally:
        val['seconds'] = time.time() - start
