from __future__ import absolute_import, print_function
import inspect
import sys
import six
import collections


def get_caller(offset=0):
    _, filename, linenum, funcname, _, _ = inspect.stack()[offset]
    return {'filename': filename,
            'linenum': linenum,
            'funcname': funcname}


def string_type():
    try:
        return basestring # noqa
    except:
        return str


def stringify(x):
    if six.PY2:
        return x
    if isinstance(x, bytes):
        return x.decode('utf-8')


class ModuleRedirector(object):
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
    assert isinstance(val, dict)
    assert isinstance(_name_, string_type())
    assert callable(decorator)
    for k, v in list(val.items()):
        if callable(v) and v.__module__ == _name_:
            decoratee = decorator(v)
            val[k] = decoratee


def pformat_prep(val):
    import s.data
    if isinstance(val, tuple) and hasattr(val, '_fields'):
        return ['namedtuple'] + [{k: v} for k, v in zip(val._fields, val)]
    elif isinstance(val, collections.Counter):
        return ['counter'] + [{k: v} for k, v in sorted(val.items(), key=lambda x: x[1], reverse=True)]
    elif isinstance(val, dict):
        return {k: pformat_prep(v) for k, v in val.items()}
    elif isinstance(val, s.data._listy_types):
        return [pformat_prep(x) for x in val]
    elif isinstance(val, set):
        return {pformat_prep(x) for x in val}
    return val
