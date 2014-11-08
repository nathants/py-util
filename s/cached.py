from __future__ import absolute_import
import collections
import functools
import s
import json
import os


# DO NOT use these to decorate class methods
# todo how to enforce this at decoration time?


_attr = '_cached_value'


def _disk_cache_path(fn):
    file_name = s.hacks.get_caller(3)['filename']
    module_name = s.shell.module_name(file_name)
    sha = s.shell.run('shasum', file_name, '| head -c7')
    func_name = fn.__name__
    return '/tmp/cache.{module_name}.{func_name}.{sha}'.format(**locals())


def disk(fn):
    path = _disk_cache_path(fn)
    @functools.wraps(fn)
    def cached_fn(*a, **kw):
        if not os.path.isfile(path):
            with open(path, 'w') as _file:
                json.dump(fn(*a, **kw), _file)
        with open(path) as _file:
            return json.load(_file)
    cached_fn.clear_cache = lambda: s.shell.run('rm -f', path)
    with s.exceptions.ignore(AttributeError):
        cached_fn = functools.wraps(callable)(cached_fn)
    return cached_fn


def func(fn):
    @functools.wraps(fn)
    def cached_fn(*a, **kw):
        if not hasattr(cached_fn, _attr):
            cached_fn.clear_cache = lambda: hasattr(cached_fn, _attr) and delattr(cached_fn, _attr)
            setattr(cached_fn, _attr, fn(*a, **kw))
        return getattr(cached_fn, _attr)
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
            key = a, kw.items()
            key = tuple(a), frozenset(kw.items())
            if key not in cache:
                result = fn(*a, **kw)
                cache[key] = result
            else:
                result = cache[key]
            while len(cache) > max_keys: # trim lru to max_keys
                cache.popitem(last=False)
            return result
        setattr(decorated, _attr, collections.OrderedDict())
        return decorated
    return decorator
