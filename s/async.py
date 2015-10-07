import s.exceptions
import os
import signal
import functools
import logging


def is_future(obj):
    with s.exceptions.ignore(AttributeError):
        object.__getattribute__(obj, 'add_done_callback')
        return True


def exceptions_kill_pid(decoratee):
    """
    Any exceptions in this decoratee will exit the main process,
    even when this decoratee is running in a thread.
    """
    exit1 = lambda: os.kill(os.getpid(), signal.SIGTERM)
    @functools.wraps(decoratee)
    def f(*a, **kw):
        try:
            return decoratee(*a, **kw)
        except SystemExit:
            exit1()
        except:
            logging.exception('')
            exit1()
    return f
