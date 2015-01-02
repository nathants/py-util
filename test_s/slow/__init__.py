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
                        proc = s.proc.new(fn, *a, _daemon=False, **kw)
                        proc.join()
                        assert proc.exitcode == 0
                        break
                except:
                    if i >= retries:
                        raise
                finally:
                    proc.terminate()
        return decorated
    return decorator
