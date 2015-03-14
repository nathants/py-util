from __future__ import print_function, absolute_import
import sys
import inspect
import functools
import traceback
import json
import logging
import time
import s.data
import s.func
import s.exceptions
import tornado.concurrent
import concurrent.futures


@s.func.optionally_parameterized_decorator
def trace(freeze=True):
    def decorator(decoratee):
        if not getattr(decoratee, '_traced', False):
            if inspect.isgeneratorfunction(decoratee):
                decoratee = _gen_type(decoratee, freeze)
            else:
                decoratee = _fn_type(decoratee, freeze)
            decoratee._traced = True
        return decoratee
    return decorator


_future_types = (tornado.concurrent.Future,
                 concurrent.futures.Future)


def _trace(val):
    # TODO this is globally disableable
    # TODO migrate to msgpack, dict keys must be str is a deal breaker
    try:
        text = json.dumps(val)
    except:
        try:
            text = json.dumps(s.data.jsonify(val))
        except:
            text = json.dumps('failed to jsonify: {}'.format(val))
    getattr(logging, 'trace', lambda x: None)(text)


def _trace_in(name, fntype, *a, **kw):
    _trace({'name': name,
            'direction': 'in',
            'fntype': fntype,
            'args': a,
            'kwargs': kw,
            'time': time.time()})


def _trace_out(name, fntype, val=None, traceback=None):
    _trace({'name': name,
            'direction': 'out',
            'fntype': fntype,
            'value': val,
            'time': time.time(),
            'traceback': traceback})


def _fn_type(decoratee, freeze):
    name = s.func.name(decoratee)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        _trace_in(name, 'fn', *a, **kw)
        try:
            if freeze:
                # with s.exceptions.update('trying to freeze args to: {name}'.format(**locals())):
                a, kw = s.data.freeze(a), s.data.freeze(kw)
            val = decoratee(*a, **kw)
            if freeze:
                # with s.exceptions.update('trying to return value from: {name}'.format(**locals())):
                val = s.data.freeze(val)
        except:
            _trace_out(name, 'fn', traceback=traceback.format_exc())
            raise
        _trace_out(name, 'fn', val=val)
        return val
    return decorated


def _gen_type(decoratee, freeze):
    name = s.func.name(decoratee)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        _trace_in(name, 'gen', *a, **kw)
        if freeze:
            # with s.exceptions.update('trying to freeze args to: {name}'.format(**locals())):
            a, kw = s.data.freeze(a), s.data.freeze(kw)
        generator = decoratee(*a, **kw)
        to_send = None
        first_send = True
        send_exception = False
        while True:
                try:
                    if freeze:
                        # with s.exceptions.update('trying to freeze send value to: {name}'.format(**locals())):
                        to_send = s.data.freeze(to_send)
                    if not first_send:
                        _trace_in(name, 'gen.send', to_send)
                    first_send = False
                    if send_exception:
                        to_yield = generator.throw(*send_exception)
                        send_exception = False
                    else:
                        to_yield = generator.send(to_send)
                    if freeze and not _is_futury(to_yield):
                        # with s.exceptions.update('trying to freeze yield value from: {name}'.format(**locals())):
                        to_yield = s.data.freeze(to_yield)
                except (tornado.gen.Return, StopIteration) as e:
                    # TODO should we be freezing this?
                    _trace_out(name, 'gen', val=getattr(e, 'value', None))
                    raise e
                except:
                    _trace_out(name, 'gen', traceback=traceback.format_exc())
                    raise
                else:
                    _trace_out(name, 'gen.yield', val=to_yield)
                try:
                    to_send = yield to_yield
                except:
                    send_exception = sys.exc_info()
    return decorated


def _is_futury(obj):
    if isinstance(obj, _future_types):
        return True
    elif isinstance(obj, (list, tuple)) and all(isinstance(x, _future_types) for x in obj):
        return True
    elif isinstance(obj, dict) and all(isinstance(x, _future_types) for x in obj.values()):
        return True
    else:
        return False
