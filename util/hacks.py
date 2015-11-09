import os
import inspect
import sys


def get_caller(offset=0):
    """
    lookup the caller of the current function from the stack,
    with optional offset to climb higher up the stack.
    """
    _, filename, linenum, funcname, _, _ = inspect.stack()[offset]
    return {'filename': filename,
            'linenum': linenum,
            'funcname': funcname}


def stringify(x):
    """
    py3k compat, for when you never ever want bytes.
    """
    if sys.version_info.major == 2:
        return x
    if isinstance(x, bytes):
        return x.decode('utf-8')


class ModuleRedirector(object):
    """
    intercept attribute lookup on a module and call a function instead.
    can optionally be triggered on all lookups, not just missing attributes.

    # simple lookup
    >>> # ModuleRedirector(__name__, lambda x: {'you tried to access': x})

    # rediculous import magic. so you can import blah, and access blah.foo, blah.bar, etc
    >>> # ModuleRedirector(__name__, lambda x: __import__('{}.{}'.format(__name__, x), fromlist='*'))

    """
    def __init__(self, name, decoratee, redirect_everything=False):
        self._orig_module_ = sys.modules[name]
        sys.modules[name] = self
        self._everything_ = redirect_everything
        decoratee.__module__ = __name__
        self.__fn__ = decoratee

    def __getattr__(self, name):
        try:
            assert not self._everything_
            return getattr(object.__getattribute__(self, '_orig_module_'), name)
        except (AssertionError, AttributeError):
            return object.__getattribute__(self, '__fn__')(name)


def decorate(val, _name_, decorator):
    """
    decorate all functions in a module
    >>> # decorate(locals(), __name__, lambda x: x)
    """
    for k, v in list(val.items()):
        if callable(v) and v.__module__ == _name_:
            val[k] = decorator(v)


def override(flag):
    """
    special flags that get popped out of sys.argv, so they can be used upstream from argparse.
    records state in an env variable so child processes don't get the override again.
    >>> # do_stuff = override('--do-stuff')
    $ python myscript.py --do-stuff
    """
    var = '_override_{}'.format(flag.strip('-'))
    if var in os.environ or flag in sys.argv:
        if flag in sys.argv:
            sys.argv.remove(flag)
        os.environ[var] = ''
        return True
