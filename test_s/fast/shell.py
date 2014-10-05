import s
import os
import mock


def test_module_name():
    val = [['a/b/c', [], ['__init__.py', 'foo.py']],
           ['a/b', ['c'], []]]
    assert s.shell._module_name('a/b/c/foo.py', val) == 'c.foo'


def test_module_name_init():
    val = [['a/b/c', [], ['__init__.py', 'foo.py']],
           ['a/b', ['c'], []]]
    assert s.shell._module_name('a/b/c/__init__.py', val) == 'c'


def test__pref_path():
    val = os.path.join(os.environ['HOME'], '.b.c.d.yaml')
    assert s.shell._pref_path('/a/b/c/d.py') == val


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
