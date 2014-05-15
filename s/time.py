from __future__ import absolute_import
import contextlib
import time
import functools
import thread
import threading
import s


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


def timeout(seconds):
    assert isinstance(seconds, (int, float)), 'seconds is not number: {} {}'.format(type(seconds), seconds)
    def decorator(decoratee):
        @functools.wraps(decoratee)
        def decorated(*a, **kw):
            do_timeout = True
            assert threading.current_thread().name == 'MainThread', 'timeout decorated funcs only work in main thread'
            def raise_timeout():
                time.sleep(seconds)
                if do_timeout:
                    thread.interrupt_main()
            s.thread.new(raise_timeout)
            try:
                return decoratee(*a, **kw)
            except KeyboardInterrupt:
                raise Exception('timed out after {}s: {}.{}'.format(seconds, decoratee.__module__, decoratee.__name__))
            finally:
                do_timeout = False
        return decorated
    return decorator
