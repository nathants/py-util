import itertools
import logging
import time
import random


def retry(f, *allowed_exceptions, times=6, sleep=1, exponent=1, silent=False):
    def fn(*a, **kw):
        for i in itertools.count():
            try:
                return f(*a, **kw)
            except allowed_exceptions:
                raise
            except Exception as e:
                if i == times:
                    raise
                if not silent:
                    logging.info(f'retrying: {f.__module__}.{f.__name__}, because of: {e}')
                time.sleep(((sleep * i if exponent else 1) ** exponent) + random.random())
    return fn
