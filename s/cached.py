import collections
import functools
import s


def func(fn):
    attr = '_cached_{}'.format(callable.__name__)
    def cached_fn(*a, **kw):
        cached_fn.clear = lambda: delattr(fn, attr)
        if not hasattr(fn, attr):
            setattr(fn, attr, fn(*a, **kw))
        return getattr(fn, attr)
    cached_fn.clear = lambda: None
    with s.exceptions.ignore(AttributeError):
        cached_fn = functools.wraps(callable)(cached_fn)
    return cached_fn


def memoize(max=1000):
    def decorator(fn):
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
