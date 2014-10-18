import s
import os
import sys
import pytest
import mock


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


def test_rel_path():
    s.shell.run('mkdir -p a/b/c')
    s.shell.run('touch a/b/__init__.py a/b/c/__init__.py a/b/c/foo.py')
    assert 'b/c/foo.py' == s.shell.rel_path(os.path.abspath('a/b/c/foo.py'))


def test_interactive_excepts_run():
    with pytest.raises(Exception):
        s.shell.run('false', interactive=True)


def test_echo_run():
    assert 'asdf' == s.shell.run('echo asdf')


def test_exitcode_run():
    assert 1 == s.shell.run('false', warn=True)['exitcode']


def test_excepts_run():
    with pytest.raises(Exception):
        s.shell.run('false')


def test_interactive_run():
    s.shell.run('true', interactive=True)
    s.shell.run('false', interactive=True, warn=True)


def test_get_or_prompt_pref():
    with s.shell.tempdir():
        with mock.patch('os.environ', {'HOME': os.getcwd()}):
            with mock.patch('six.moves.input', mock.Mock(return_value='bar')) as _raw_input:
                assert s.shell.get_or_prompt_pref('foo', __file__) == 'bar'
                assert _raw_input.call_count == 1
                assert s.shell.get_or_prompt_pref('foo', __file__) == 'bar'
                assert _raw_input.call_count == 1
                with open(s.shell.files()[0]) as _file:
                    assert _file.read().strip() == 'foo: bar'
