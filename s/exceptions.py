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
