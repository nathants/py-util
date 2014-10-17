import os
import s
import sys


_keys = list(sys.modules.keys())


def setup_module():
    s.log.setup()


def setup_function(fn):
    fn.tempdir_context = s.shell.tempdir()
    fn.tempdir_context.__enter__()
    for k, v in list(sys.modules.items()):
        if k not in _keys:
            del sys.modules[k]
    sys.path.insert(0, os.getcwd())


def teardown_function(fn):
    fn.tempdir_context.__exit__(None, None, None)
    sys.path.pop(0)


def test_collect_tests():
    with open('foo.py', 'w') as fio:
        fio.write("""
def test1():
    pass
""")
    assert s.test._collect_tests('foo.py') == ["<Function 'test1'>"]


def test_climb():
    s.shell.run('mkdir -p 1/2/3 && touch 1/a 1/2/b 1/2/3/s')
    x = os.getcwd()
    with s.shell.cd('1/2/3'):
        assert list(s.shell.climb())[0] == [os.path.join(x, '1/2/3'), [], ['s']]
        assert list(s.shell.climb())[1] == [os.path.join(x, '1/2'), ['3'], ['b']]
        assert list(s.shell.climb())[2] == [os.path.join(x, '1'), ['2'], ['a']]


def test_fast_test_files():
    s.shell.run('mkdir -p .git test_foo/fast foo')
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py test_foo/fast/bar.py foo/bar.py foo/__init__.py')
    assert set(s.test.fast_test_files()) == {os.path.abspath('test_foo/fast/__init__.py'),
                                             os.path.abspath('test_foo/fast/bar.py')}


def test_code_files_and_python_packages():
    s.shell.run('mkdir -p .git foo && touch foo/bar.py foo/__init__.py')
    assert s.test._python_packages(s.shell.walk()) == [os.path.abspath('foo')]
    assert set(s.test.code_files()) == {os.path.abspath('foo/bar.py'),
                                        os.path.abspath('foo/__init__.py')}


def test_import_syntax_error():
    with open('test_foo.py', 'w') as fio:
        fio.write("""
def test1():
1/0
""")
    val = s.test._test('test_foo.py')
    assert 'IndentationError: expected an indented block' in val[0]['result']


def test_fail():
    with open('test_foo.py', 'w') as fio:
        fio.write("""
def test1():
   x, y = 1, 3
   assert x == y
""")
    val = s.test._test('test_foo.py')
    assert val[0]['result'].splitlines()[-3].endswith("assert 1 == 3") # make sure we are getting the _pytest_insight output


def test_pass():
    with open('test_foo.py', 'w') as fio:
        fio.write("""
def test1():
   x, y = 1, 1
   assert x == y
""")
    assert not s.test._test('test_foo.py')[0]['result']


def test_run_tests_once_fail():
    s.shell.run('mkdir .git')
    with s.shell.cd('test_foo/fast'):
        with open('test1.py', 'w') as fio:
            fio.write("""
def test1():
    pass
""")
        with open('test2.py', 'w') as fio:
            fio.write("""
def test2():
    1/0
""")
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py')
    val = s.test.run_tests_once()
    assert len(val) == 3
    assert len([x for x in val if x[0]['result']]) == 1


def test_run_tests_once_pass():
    s.shell.run('mkdir .git')
    with s.shell.cd('test_foo/fast'):
        with open('test1.py', 'w') as fio:
            fio.write("""
def test1():
    pass
""")
        with open('test2.py', 'w') as fio:
            fio.write("""
def test2():
    pass
""")
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py')
    assert [x[0]['result'] for x in s.test.run_tests_once()] == [None, False, False]


def test_climb_git_root():
    with s.shell.tempdir():
        path = os.getcwd()
        s.shell.run('mkdir .git')
        with s.shell.cd('a/b/c'):
            assert path == s.func.thrush(
                s.shell.climb(),
                s.test._git_root,
            )


def test_test_file():
    s.shell.run('mkdir -p test_foo/fast foo && touch test_foo/__init__.py test_foo/fast/__init__.py test_foo/fast/bar.py foo/bar.py foo/__init__.py')
    code_file = os.path.abspath('foo/bar.py')
    test_file = os.path.abspath('test_foo/fast/bar.py')
    assert s.test.test_file(code_file) == test_file


def test_code_file():
    s.shell.run('mkdir -p test_foo/fast foo && touch test_foo/__init__.py test_foo/fast/__init__.py test_foo/fast/bar.py foo/bar.py foo/__init__.py')
    code_file = os.path.abspath('foo/bar.py')
    test_file = os.path.abspath('test_foo/fast/bar.py')
    assert s.test.code_file(test_file) == code_file
