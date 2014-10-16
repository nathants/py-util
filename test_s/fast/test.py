import s
import os


def test_python_packages():
    data = [['/foo', ['bar'], []],
            ['/foo/bar', ['asdf'], ['__init__.py']],
            ['/foo/bar/asdf', [], ['__init__.py']]]
    assert s.test._python_packages(data) == ['/foo/bar']


def test__test_file():
    assert s.test._test_file('foo/bar.py') == 'test_foo/fast/bar.py'


def test_handles_init__test_file():
    assert s.test._test_file('foo/__init__.py') == 'test_foo/fast/__init__.py'


def test__code_file():
    assert s.test._code_file(s.test._test_file('foo/bar.py')) == 'foo/bar.py'


def test_handles_init__code_file():
    assert s.test._code_file(s.test._test_file('foo/__init__.py')) == 'foo/__init__.py'


def test_filter_test_files():
    val = [['test_module', ['fast'], ['__init__.py']],
           ['test_module/fast', [], ['__init__.py', 'test1.py', 'test1.pyc', 'test2.py', '.#test2.py', 'test2_flymake.py']],
           ['module', [], ['__init__.py']]]
    assert s.test._filter_test_files(val) == [os.path.join('test_module/fast', x) for x in ['__init__.py', 'test1.py', 'test2.py']]
