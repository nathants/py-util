import logging
import contextlib
import types

@contextlib.contextmanager
def ignore(*exceptions):
    if exceptions:
        try:
            yield
        except exceptions:
            pass
        except:
            raise
    else:
        try:
            yield
        except:
            pass

@contextlib.contextmanager
def update(fn_or_str, *exceptions, **kw):
    try:
        yield
    except Exception as e:
        if isinstance(e, exceptions) or not exceptions:
            try:
                msg = e.args[0]
            except:
                msg = ''
            if kw.get('when', lambda x: True)(msg):
                if isinstance(fn_or_str, types.FunctionType):
                    e.args = (fn_or_str(msg),) + e.args[1:]
                else:
                    e.args = (msg + '\n' + fn_or_str,) + e.args[1:]
        raise

@contextlib.contextmanager
def log():
    try:
        yield
    except:
        logging.exception('')
        raise
