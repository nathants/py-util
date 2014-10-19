from __future__ import absolute_import
import collections
import functools
import s


# DO NOT use these to decorate class methods
# todo how to enforce this at decoration time?


_attr = '_cached_value'


def func(fn):
    def cached_fn(*a, **kw):
        cached_fn.clear_cache = lambda: delattr(fn, _attr)
        if not hasattr(fn, _attr):
            setattr(fn, _attr, fn(*a, **kw))
        return getattr(fn, _attr)
    cached_fn.clear_cache = lambda: None
    with s.exceptions.ignore(AttributeError):
        cached_fn = functools.wraps(callable)(cached_fn)
    return cached_fn


@s.hacks.optionally_parameterized_decorator
def memoize(max_keys=10000):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*a, **kw):
            cache = getattr(decorated, _attr)
            key = tuple(map(s.data.immutalize, [a, kw.items()]))
            if key not in cache:
                result = fn(*a, **kw)
            else:
                result = cache.pop(key)
            cache[key] = result
            while len(cache) > max_keys: # trim lru to max_keys
                cache.popitem(last=False)
            return result
        setattr(decorated, _attr, collections.OrderedDict())
        return decorated
    return decorator
