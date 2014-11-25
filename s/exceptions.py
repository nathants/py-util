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


def update(exception, fn):
    try:
        msg = exception.args[0]
    except:
        msg = ''
    exception.args = (fn(msg),) + exception.args[1:]
    return exception
