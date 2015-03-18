from __future__ import print_function, absolute_import
import uuid
import sys
import inspect
import functools
import traceback
import time
import s.data
import s.func
import s.exceptions
import s.cached
import tornado.concurrent
import concurrent.futures
import msgpack


disabled = False


@s.func.optionally_parameterized_decorator
def trace(freeze=True):
    def decorator(decoratee):
        # return decoratee
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


def _pretty_objects(x):
    x = str(x)
    if ' at 0x' in x:
        x = x.split()[0].split('.')[-1]
    return '<{}>'.format(x.strip('<>'))


def _trace_path():
    when = time.time()
    entry_point = '.'.join(sys.argv[0].split('.')[0].split('/')[-2:])
    args = '.'.join(x for x in sys.argv[1:] if not x.startswith('-'))
    args = ':' + args if args else ''
    return '/tmp/{entry_point}{args}:{when}:trace.log'.format(**locals())


trace_path = _trace_path()


def _trace(val):
    return
    val = msgpack.dumps(val, default=_pretty_objects)
    with open(trace_path, 'ab') as f:
        f.write(val + b'\r\n')


def _trace_in(uuid, yield_uuid, name, fntype, *a, **kw):
    if not disabled:
        _trace({'uuid': uuid,
                'yield_uuid': yield_uuid,
                'name': name,
                'direction': 'in',
                'fntype': fntype,
                'args': a,
                'kwargs': kw,
                'time': time.time()})


def _trace_out(uuid, yield_uuid, name, fntype, val=None, traceback=None):
    if not disabled:
        _trace({'uuid': uuid,
                'yield_uuid': yield_uuid,
                'name': name,
                'direction': 'out',
                'fntype': fntype,
                'value': val,
                'time': time.time(),
                'traceback': traceback})


def _fn_type(decoratee, freeze):
    name = s.func.name(decoratee)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        uid = str(uuid.uuid4())
        _trace_in(uid, None, name, 'fn', *a, **kw)
        try:
            if freeze:
                # with s.exceptions.update('trying to freeze args to: {name}'.format(**locals())):
                a, kw = s.data.freeze(a), s.data.freeze(kw)
            val = decoratee(*a, **kw)
            if freeze:
                # with s.exceptions.update('trying to return value from: {name}'.format(**locals())):
                val = s.data.freeze(val)
        except:
            _trace_out(uid, None, name, 'fn', traceback=traceback.format_exc())
            raise
        _trace_out(uid, None, name, 'fn', val=val)
        return val
    return decorated


def _gen_type(decoratee, freeze):
    name = s.func.name(decoratee)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        uid = str(uuid.uuid4())
        yield_uid = None
        to_send = None
        first_send = True
        send_exception = False
        _trace_in(uid, yield_uid, name, 'gen', *a, **kw)
        if freeze:
            # with s.exceptions.update('trying to freeze args to: {name}'.format(**locals())):
            a, kw = s.data.freeze(a), s.data.freeze(kw)
        generator = decoratee(*a, **kw)
        while True:
                try:
                    if freeze:
                        # with s.exceptions.update('trying to freeze send value to: {name}'.format(**locals())):
                        to_send = s.data.freeze(to_send)
                    if not first_send:
                        _trace_in(uid, yield_uid, name, 'gen.send', to_send)
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
                    _trace_out(uid, None, name, 'gen', val=getattr(e, 'value', None))
                    raise e
                except:
                    _trace_out(uid, None, name, 'gen', traceback=traceback.format_exc())
                    raise
                else:
                    yield_uid = str(uuid.uuid4())
                    _trace_out(uid, yield_uid, name, 'gen.yield', val=to_yield)
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
