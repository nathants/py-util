from __future__ import print_function, absolute_import
import stopit
import s
import functools


@s.hacks.optionally_parameterized_decorator
def flaky(retries=3, timeout=2):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*a, **kw):
            for i in range(100):
                try:
                    with stopit.SignalTimeout(timeout, False):
                        fn(*a, **kw)
                        break
                except:
                    if i >= retries:
                        raise
        return decorated
    return decorator
