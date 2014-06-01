import s
import pytest


def test_module_name():
    val = [['a/b/c', [], ['__init__.py', 'foo.py']],
           ['a/b', ['c'], []]]
    assert s.shell._module_name('a/b/c/foo.py', val) == 'c.foo'


def test_module_name_init():
    val = [['a/b/c', [], ['__init__.py', 'foo.py']],
           ['a/b', ['c'], []]]
    assert s.shell._module_name('a/b/c/__init__.py', val) == 'c'
