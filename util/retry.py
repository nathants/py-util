import itertools
import logging
import time
import traceback

def retry(f, *allowed_exceptions, allowed_exception_fn=None, times=6, sleep=1, exponent=1, silent=False, max_seconds=0, stacktrace=True):
    def fn(*a, **kw):
        start = time.time()
        for i in itertools.count():
            try:
                return f(*a, **kw)
            except allowed_exceptions:
                raise
            except (SystemExit, Exception) as e:
                if allowed_exception_fn and allowed_exception_fn(e):
                    raise
                duration = time.time() - start
                if i == times or (max_seconds and duration >= max_seconds):
                    raise
                if not silent:
                    if stacktrace:
                        logging.exception(f'retrying: {f.__module__}.{f.__name__}')
                    else:
                        e = e if str(e).strip() else '\n' + traceback.format_exc()
                        logging.info(f'retrying: {f.__module__}.{f.__name__}, because of: {e}')
                if exponent:
                    amount = (sleep * i) ** exponent
                else:
                    amount = sleep
                if max_seconds and duration + amount > max_seconds:
                    amount = max_seconds - duration
                time.sleep(amount)
    return fn
