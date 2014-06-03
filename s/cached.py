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


def memoize(max=1000):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*a, **kw):
            key = tuple(map(s.data.immutalize, [a, kw.items()]))
            if key not in decorated._data:
                result = fn(*a, **kw)
            else:
                result = decorated._data.pop(key)
            decorated._data[key] = result
            while len(decorated._data) > max: # trim lru to max
                decorated._data.popitem(last=False)
            return result
        decorated._data = collections.OrderedDict()
        return decorated
    return decorator
