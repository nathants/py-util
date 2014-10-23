import s
import os


def test__module_name():
    val = [['a/b/c', [], ['__init__.py', 'foo.py']],
           ['a/b', ['c'], []]]
    assert s.shell._module_name('a/b/c/foo.py', val) == 'c.foo'


def test_init__module_name():
    val = [['a/b/c', [], ['__init__.py', 'foo.py']],
           ['a/b', ['c'], []]]
    assert s.shell._module_name('a/b/c/__init__.py', val) == 'c'


def test__pref_path():
    val = os.path.join(os.environ['HOME'], '.b.c.d.yaml')
    assert s.shell._pref_path('/a/b/c/d.py') == val
