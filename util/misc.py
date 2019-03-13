import util.exceptions
import os
import signal
import functools
import logging

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
        except:
            logging.exception('')
            os.kill(pid, signal.SIGTERM)
    return decorated
