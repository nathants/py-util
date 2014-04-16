import s
import os

s.log.setup(pprint=True, level='debug')


def test_python_packages():
    data = [['/foo', ['bar'], []],
            ['/foo/bar', ['asdf'], ['__init__.py']],
            ['/foo/bar/asdf', [], ['__init__.py']]]
    assert s.test._python_packages(data) == ['bar']


def test_test_file():
    assert s.test._test_file('foo/bar.py') == os.path.join(s.test._test_dir, 'test-foo-bar.py')


def test_test_file_init():
    assert s.test._test_file('foo/__init__.py') == os.path.join(s.test._test_dir, 'test-foo-__init__.py')


def test_code_file():
    assert s.test._code_file(s.test._test_file('foo/bar.py')) == 'foo/bar.py'


def test_code_file_init():
    assert s.test._code_file(s.test._test_file('foo/__init__.py')) == 'foo/__init__.py'


def test_filter_test_files():
    val = [[s.test._test_dir, [], ['test1.py', 'test2.py']],
           ['module', [], ['__init__.py']]]
    assert s.test._filter_test_files(val) == [os.path.join(s.test._test_dir, x) for x in ['test1.py', 'test2.py']]


def test_filter_test_files_git():
    val = [[os.path.join('/tmp/tdHuDDvMYt', s.test._test_dir), [], ['test.py']],
           ['/tmp/tdHuDDvMYt/tests', ['unit'], []],
           ['/tmp/tdHuDDvMYt', ['.git', 'tests'], []]]
    assert s.test._filter_test_files(val) == [os.path.join(s.test._test_dir, 'test.py')]
