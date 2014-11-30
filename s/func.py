from __future__ import absolute_import, print_function
import s
import sys


def inline(*funcs):
    for fn in funcs:
        assert callable(fn), '{} is not callable'.format(fn)
    def _fn(val):
        for func in funcs:
            val = func(val)
        return val
    return _fn


def pipe(value, *funcs):
    return inline(*funcs)(value)


def name(fn):
    with s.exceptions.ignore():
        return '{}.{}'.format(fn.__module__, fn.__name__)
    with s.exceptions.ignore():
        return fn.__name__
    with s.exceptions.ignore():
        return str(fn)
    return fn


def source(fn):
    try:
        filename, linenum = fn.func_code.co_filename, fn.func_code.co_firstlineno
        with open(filename) as _file:
            text = _file.read().splitlines()[linenum - 1]
            return '{filename}:{linenum} => {text}'.format(**locals())
    except:
        return name(fn)


def module_name(fn):
    module = fn.__module__
    with s.exceptions.ignore():
        if module == '__main__':
            for x in range(20):
                _module = '.'.join(__file__.split('.')[0].split('/')[x:])
                if _module in sys.modules:
                    return _module
    return module
