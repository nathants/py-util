import sys
import inspect
import collections

def get_caller(offset=0):
    _, filename, lineum, funcname, _, _ = inspect.stack()[offset]
    return collections.namedtuple('caller', 'filename linenum funcname')(filename, lineum, funcname)


def string_type():
    try:
        return basestring
    except:
        return str


def stringify(x):
    if sys.version_info < (3,):
        return x
    if isinstance(x, bytes):
        return x.decode('utf-8')


class ModuleRedirector(object):
    def __init__(self, name, fn, redirect_everything=False):
        self.__orig_module = sys.modules[name]
        sys.modules[name] = self
        self.__everything = redirect_everything
        self.__fn = fn

    def __getattr__(self, name):
        try:
            assert not self.__everything
            return getattr(self.__orig_module, name)
        except (AssertionError, AttributeError):
            return self.__fn(name)


def decorate(val, _name_, decorator):
    assert isinstance(val, dict)
    assert isinstance(_name_, string_type())
    assert callable(decorator)
    for k, v in list(val.items()):
        if callable(v) and v.__module__ == _name_:
            fn = decorator(v)
            val[k] = fn
