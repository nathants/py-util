import s
import os
import sys
import pytest


_keys = list(sys.modules.keys())


def setup_function(fn):
    fn.ctx = s.shell.tempdir()
    fn.ctx.__enter__()
    for k, v in list(sys.modules.items()):
        if k not in _keys:
            del sys.modules[k]
    sys.path.insert(0, os.getcwd())


def teardown_function(fn):
    fn.ctx.__exit__(None, None, None)
    sys.path.pop(0)


def test_module_name():
    s.shell.run('mkdir -p a/b/c')
    s.shell.run('touch a/b/__init__.py a/b/c/__init__.py a/b/c/foo.py')
    assert 'b.c.foo' == s.shell.module_name(os.path.abspath('a/b/c/foo.py'))


def test_interactive_excepts():
    with pytest.raises(Exception):
        s.shell.run('false', interactive=True)


def test_callback():
    val = []
    cb = lambda x: val.append(x)
    s.shell.run('echo asdf', callback=cb)
    assert val == ['asdf']


def test_echo():
    assert 'asdf' == s.shell.run('echo asdf')


def test_exitcode():
    assert 1 == s.shell.run('false', warn=True).exitcode


def test_excepts():
    with pytest.raises(Exception):
        s.shell.run('false')


def test_interactive():
    s.shell.run('true', interactive=True)
    s.shell.run('false', interactive=True, warn=True)


s.hacks.decorate(globals(), __name__, s.fn.badfunc)
