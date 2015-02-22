from __future__ import absolute_import, print_function
import s
import sys


def pipe_last(value, *args):
    for arg in args:
        if callable(arg):
            value = arg(value)
        else:
            fn, arg = arg[0], list(arg[1:]) + [value]
            value = fn(*arg)
    return value


def pipe_some_last(value, *args):
    for arg in args:
        if value is None:
            return
        elif callable(arg):
            value = arg(value)
        else:
            fn, arg = arg[0], list(arg[1:]) + [value]
            value = fn(*arg)
    return value


def pipe(value, *args):
    for arg in args:
        if callable(arg):
            value = arg(value)
        else:
            fn, arg = arg[0], arg[1:]
            value = fn(value, *arg)
    return value


def pipe_some(value, *args):
    for arg in args:
        if value is None:
            return
        elif callable(arg):
            value = arg(value)
        else:
            fn, arg = arg[0], arg[1:]
            value = fn(value, *arg)
    return value


def name(fn):
    with s.exceptions.ignore():
        return '{}:{}'.format(fn.__module__, fn.__name__)
    with s.exceptions.ignore():
        return fn.__name__
    with s.exceptions.ignore():
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
        with s.exceptions.ignore():
            for x in range(20):
                module = '.'.join(__file__.split('.')[0].split('/')[x:])
                if module in sys.modules:
                    return module
