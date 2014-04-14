import sys


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
