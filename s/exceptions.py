from __future__ import absolute_import
import contextlib


@contextlib.contextmanager
def ignore(*exceptions):
    exceptions = exceptions or Exception
    try:
        yield
    except exceptions:
        pass
    except:
        raise


@contextlib.contextmanager
def update(fn, *exceptions):
    try:
        yield
    except (exceptions or Exception) as e:
        try:
            msg = e.args[0]
        except:
            msg = ''
        e.args = (fn(msg),) + e.args[1:]
        raise
