import functools
import inspect
import logging
import os
import signal
import sys
import util.exceptions

def is_future(obj):
    with util.exceptions.ignore(AttributeError):
        object.__getattribute__(obj, 'add_done_callback')
        return True

def exceptions_kill_pid(decoratee):
    """
    Any exceptions in this decoratee will exit the main process,
    even when this decoratee is running in a thread.
    """
    pid = os.getpid()
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        try:
            return decoratee(*a, **kw)
        except SystemExit:
            os.kill(pid, signal.SIGTERM)
            raise
        except:
            logging.exception('')
            os.kill(pid, signal.SIGTERM)
            raise
    return decorated

def get_caller(offset=0):
    """
    lookup the caller of the current function from the stack,
    with optional offset to climb higher up the stack.
    """
    _, filename, linenum, funcname, _, _ = inspect.stack()[offset]
    return {'filename': filename,
            'linenum': linenum,
            'funcname': funcname}

def decorate(val, _name_, decorator):
    """
    decorate all functions in a module
    >>> # decorate(locals(), __name__, lambda x: x)
    """
    for k, v in list(val.items()):
        if callable(v) and v.__module__ == _name_:
            val[k] = decorator(v)

def override(flag):
    """
    special flags that get popped out of sys.argv, so they can be used upstream from argparse.
    records state in an env variable so child processes respect a parent's override.
    >>> do_stuff = override('--do-stuff')
    $ python myscript.py --do-stuff
    """
    var = '_override_{}'.format(flag.strip('-'))
    if var in os.environ or flag in sys.argv:
        if flag in sys.argv:
            sys.argv.remove(flag)
        os.environ[var] = ''
        return True
