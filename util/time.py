import signal
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

@contextlib.contextmanager
def timeout(seconds=1, message='timeout'):
    def fn(*_):
        raise Exception('%s after %s seconds' % (message, seconds)) from None
    signal.signal(signal.SIGALRM, fn)
    signal.alarm(seconds)
    try:
        yield
    except:
        raise
    finally:
        signal.alarm(0)
