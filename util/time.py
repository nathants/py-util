import signal
import contextlib
import time

@contextlib.contextmanager
def timer(msg=None, print_fn=print):
    val = {'seconds': None}
    start = time.time()
    try:
        yield val
    except:
        raise
    finally:
        val['seconds'] = time.time() - start
        if msg:
            print_fn(msg, int(val['seconds']), 'seconds')

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
