import itertools
import logging
import time
import random

def retry(f, *allowed_exceptions, allowed_exception_fn=None, times=6, sleep=1, exponent=1, silent=False):
    def fn(*a, **kw):
        for i in itertools.count():
            try:
                return f(*a, **kw)
            except allowed_exceptions:
                raise
            except Exception as e:
                if allowed_exception_fn and allowed_exception_fn(e):
                    raise
                if i == times:
                    raise
                if not silent:
                    logging.info(f'retrying: {f.__module__}.{f.__name__}, because of: {e}')
                if exponent:
                    amount = (sleep * i) ** exponent
                else:
                    amount = sleep
                time.sleep(amount + random.random())
    return fn
