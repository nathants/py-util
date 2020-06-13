import functools
import types
import util.exceptions
import inspect
import sys

def name(fn):
    with util.exceptions.ignore():
        return '{}.{}'.format(fn.__module__, fn.__name__)
    with util.exceptions.ignore():
        return fn.__name__
    with util.exceptions.ignore():
        return str(fn)
    return fn

def source(fn):
    try:
        filename, linenum = fn.func_code.co_filename, fn.func_code.co_firstlineno
        with open(filename) as f:
            text = f.read().splitlines()[linenum - 1]
            return '{filename}:{linenum} => {text}'.format(**locals())
    except:
        return name(fn)

def module_name(fn):
    if fn.__module__ != '__main__':
        return fn.__module__
    else:
        with util.exceptions.ignore():
            for x in range(20):
                module = '.'.join(__file__.split('.')[0].split('/')[x:])
                if module in sys.modules:
                    return module

def optionally_parameterized_decorator(decoratee):
    """
    wont work if you decorator can be invoked with a single function argument,
    which is the same signature as decorator usage.
    """
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        method = (len(a) == 2
                  and inspect.ismethod(getattr(a[0], decoratee.__name__, None))
                  and isinstance(a[1], types.FunctionType)
                  and not kw)
        function = (len(a) == 1
                    and isinstance(a[0], types.FunctionType)
                    and not kw)
        if method: # called without params
            self, fn = a
            return decoratee(self)(fn)
        elif function: # called without params
            [fn] = a
            return decoratee()(fn)
        else: # called with params
            return decoratee(*a, **kw)
    return decorated
