from __future__ import absolute_import
import subprocess
import inspect
import collections
import functools
import s.exceptions
import s.hacks
import s.func
import json
import os


_attr = '_cached_value'


def _disk_cache_path(fn):
    try:
        file_name = s.hacks.get_caller(3)['filename'].strip()
    except IndexError:
        file_name = s.hacks.get_caller(2)['filename'].strip()
    sha = s.hacks.stringify(subprocess.check_output(['shasum', file_name])[:7])
    name = '.'.join(file_name.split('.py')[0].split('/')[-2:])
    return '/tmp/cache.%s.%s.%s' % (name, fn.__name__, sha)


def disk(fn):
    path = _disk_cache_path(fn)
    @functools.wraps(fn)
    def cached_fn(*a, **kw):
        assert not a or not inspect.ismethod(getattr(a[0], getattr(fn, '__name__', ''), None)), 'cached.disk does not work with methods'
        if not os.path.isfile(path):
            with open(path, 'w') as f:
                json.dump(fn(*a, **kw), f)
        with open(path) as f:
            return json.load(f)
    cached_fn.clear_cache = lambda: subprocess.check_call(['rm', '-f', path])
    with s.exceptions.ignore(AttributeError):
        cached_fn = functools.wraps(callable)(cached_fn)
    return cached_fn


def is_cached(fn):
    return hasattr(fn, _attr)


def func(fn):
    @functools.wraps(fn)
    def cached_fn(*a, **kw):
        assert not a or not inspect.ismethod(getattr(a[0], getattr(fn, '__name__', ''), None)), 'cached.disk does not work with methods'
        if not hasattr(cached_fn, _attr):
            cached_fn.clear_cache = lambda: hasattr(cached_fn, _attr) and delattr(cached_fn, _attr)
            setattr(cached_fn, _attr, fn(*a, **kw))
        return getattr(cached_fn, _attr)
    cached_fn.clear_cache = lambda: None
    with s.exceptions.ignore(AttributeError):
        cached_fn = functools.wraps(callable)(cached_fn)
    return cached_fn


@s.func.optionally_parameterized_decorator
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
