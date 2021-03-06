import os
import threading
import subprocess
import time
import hashlib
import inspect
import collections
import functools
import util.exceptions
import util.misc
import util.func
import json

_attr = '_cached_value'

_cache_root = os.environ.get('CACHED_ROOT', '/tmp')

def _disk_cache_path(fn):
    try:
        file_name = util.misc.get_caller(3)['filename'].strip()
    except IndexError:
        file_name = util.misc.get_caller(2)['filename'].strip()
    with open(file_name, 'rb') as f:
        sha = hashlib.sha1(f.read()).hexdigest()[:20]
    name = '.'.join(file_name.split('.py')[0].split('/')[-2:])
    return f'{_cache_root}/cache.{name}.{fn.__name__}.{sha}'

@util.func.optionally_parameterized_decorator
def disk(invalidate_on_source_hash=True, max_age_seconds=0):
    def decorator(fn):
        path = _disk_cache_path(fn)
        if not invalidate_on_source_hash:
            path = '.'.join(path.split('.')[:-1])
        @functools.wraps(fn)
        def cached_fn(*a, **kw):
            assert not a or not inspect.ismethod(getattr(a[0], getattr(fn, '__name__', ''), None)), 'cached.disk does not work with methods'
            try:
                with open(path) as f:
                    data = json.load(f)
                    assert not max_age_seconds or time.time() - data['time'] < max_age_seconds
                    return data['value']
            except:
                with open(path, 'w') as f:
                    val = fn(*a, **kw)
                    json.dump({'value': val, 'time': time.time()}, f)
                return val
        cached_fn.clear_cache = lambda: subprocess.check_call(['rm', '-f', path])
        return cached_fn
    return decorator

@util.func.optionally_parameterized_decorator
def disk_memoize(invalidate_on_source_hash=True, max_age_seconds=0):
    def decorator(fn):
        path = _disk_cache_path(fn)
        if not invalidate_on_source_hash:
            path = '.'.join(path.split('.')[:-1])
        @functools.wraps(fn)
        def cached_fn(*a, **kw):
            assert not a or not inspect.ismethod(getattr(a[0], getattr(fn, '__name__', ''), None)), 'cached.disk does not work with methods'
            key = a, kw.items()
            key = ';'.join(map(str, (list(a) + sorted(kw.items(), key=lambda x: x[0]))))
            hash = hashlib.sha1(key.encode('utf-8')).hexdigest()
            _path = '%s_%s' % (path, hash)
            try:
                with open(_path) as f:
                    data = json.load(f)
                    assert not max_age_seconds or time.time() - data['time'] < max_age_seconds
                    return data['value']
            except:
                with open(_path, 'w') as f:
                    val = fn(*a, **kw)
                    json.dump({'value': val, 'time': time.time()}, f)
                return val
        cached_fn.clear_cache = lambda: subprocess.check_call('rm -rf %s*' % path, shell=True)
        return cached_fn
    return decorator

def is_cached(fn):
    return hasattr(fn, _attr)

def func(fn):
    @functools.wraps(fn)
    def cached_fn(*a, **kw):
        assert not a or not inspect.ismethod(getattr(a[0], getattr(fn, '__name__', ''), None)), 'cached.func does not work with methods'
        if not hasattr(cached_fn, _attr):
            cached_fn.clear_cache = lambda: hasattr(cached_fn, _attr) and delattr(cached_fn, _attr)
            setattr(cached_fn, _attr, fn(*a, **kw))
        return getattr(cached_fn, _attr)
    cached_fn.clear_cache = lambda: None
    return cached_fn

def threadsafe(fn):
    @memoize
    def memoized_fn(ident):
        return fn()
    @functools.wraps(fn)
    def cached_fn():
        return memoized_fn(threading.get_ident())
    cached_fn.clear_cache = lambda: memoized_fn.clear_cache()
    return cached_fn

@util.func.optionally_parameterized_decorator
def memoize(max_keys=1000000, max_age_seconds=0):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*a, **kw):
            cache = getattr(decorated, _attr)
            key = a, kw.items()
            key = tuple(a), frozenset(kw.items())
            if key not in cache:
                result = fn(*a, **kw)
                cache[key] = result, time.time()
            else:
                result, time_seconds = cache[key]
                age_seconds = time.time() - time_seconds
                if max_age_seconds and age_seconds > max_age_seconds:
                    result = fn(*a, **kw)
                    cache[key] = result, time.time()
            while len(cache) > max_keys: # trim lru to max_keys
                cache.popitem(last=False)
            return result
        setattr(decorated, _attr, collections.OrderedDict())
        decorated.clear_cache = lambda: setattr(decorated, _attr, collections.OrderedDict())
        return decorated
    return decorator
