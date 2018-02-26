import itertools
import logging
import time
import random


def retry(f, times=6, sleep=1, exponent=1):
    def fn(*a, **kw):
        for i in itertools.count():
            try:
                return f(*a, **kw)
            except Exception as e:
                if i == times:
                    raise
                logging.info(f'retrying: {f.__module__}.{f.__name__}, because of: {e}')
                time.sleep((sleep ** exponent) + random.random())
    return fn
