from __future__ import absolute_import
import contextlib
import types


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
def update(fn_or_str, *exceptions):
    try:
        yield
    except Exception as e:
        if type(e) in exceptions:
            try:
                msg = e.args[0]
            except:
                msg = ''
            if isinstance(fn_or_str, types.FunctionType):
                e.args = (fn_or_str(msg),) + e.args[1:]
            else:
                e.args = (msg + fn_or_str,) + e.args[1:]
        raise
