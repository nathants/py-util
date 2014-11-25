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


def append(exception, message):
    try:
        msg = exception.args[0]
    except:
        msg = ''
    exception.args = (msg + message,) + exception.args[1:]
    return exception
