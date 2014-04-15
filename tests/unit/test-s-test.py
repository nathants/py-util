import s
import os


def test_integration1():
    with s.shell.tempdir():
        s.shell.run('mkdir -p .git tests/unit')
        with open('tests/unit/test_foo.py', 'w') as _file:
            _file.write("""def test1(): pass""")
        assert s.test._collect_tests('tests/unit/test_foo.py') == ["<Function 'test1'>"]

def test_integration2():
    with s.shell.tempdir():
        s.shell.run('mkdir -p 1/2/3 && touch 1/a 1/2/b 1/2/3/s')
        x = os.getcwd()
        with s.shell.cd('1/2/3'):
            assert list(s.test._climb())[0] == [os.path.join(x, '1/2/3'), [], ['s']]
            assert list(s.test._climb())[1] == [os.path.join(x, '1/2'), ['3'], ['b']]
            assert list(s.test._climb())[2] == [os.path.join(x, '1'), ['2'], ['a']]

def test_integration3():
    with s.shell.tempdir():
        s.shell.run('mkdir -p .git tests/unit foo && touch tests/unit/test-foo-bar.py foo/bar.py foo/__init__.py')
        os.chdir('tests/unit')
        assert s.test.all_test_files() == ['tests/unit/test-foo-bar.py']

def test_integration4():
    with s.shell.tempdir():
        s.shell.run('mkdir -p .git foo && touch foo/bar.py foo/__init__.py')
        assert s.test._python_packages(os.walk('.')) == ['foo']
        assert set(s.test.all_code_files()) == {'foo/bar.py', 'foo/__init__.py'}


def test_100():
    data = [['/foo', ['bar'], []],
            ['/foo/bar', ['asdf'], ['__init__.py']],
            ['/foo/bar/asdf', [], ['__init__.py']]]
    assert s.test._python_packages(data) == ['bar']

def test_101():
    assert s.test._test_file('foo/bar.py') == 'tests/unit/test-foo-bar.py'

def test_101():
    assert s.test._test_file('foo/__init__.py') == 'tests/unit/test-foo-__init__.py'

def test_101():
    assert s.test._code_file(s.test._test_file('foo/bar.py')) == 'foo/bar.py'

def test_101():
    assert s.test._code_file(s.test._test_file('foo/__init__.py')) == 'foo/__init__.py'

def test1():
    with s.shell.tempdir():
        with open('test.py', 'w') as io:
            io.write("""
def test1():
   x, y = 1, 2
   assert x == y
""")
        assert s.test._test('test.py')

def test11():
    with s.shell.tempdir():
        with open('test.py', 'w') as io:
            io.write("""
def test1():
   x, y = 1, 1
   assert x == y
""")
        assert not s.test._test('test.py')


def test2():
    with s.shell.tempdir():
        with open('test.py', 'w') as fio:
            fio.write("""
def test1():
   x, y = 1, 2
   assert x == y
""")
        assert s.test.climb_and_test('test.py')

def test22():
    with s.shell.tempdir():
        with open('test.py', 'w') as fio:
            fio.write("""
def test1():
   x, y = 1, 1
   assert x == y
""")
        assert not s.test.climb_and_test('test.py')


def test3():
    with s.shell.tempdir():
        s.shell.run('mkdir -p a/b/c && touch file')
        path = os.path.abspath('file')
        with s.shell.cd('a/b/c'):
            assert path == s.test._climb_find_abspath('file')


def test4():
    with s.shell.tempdir():
        s.shell.run('mkdir .git')
        with s.shell.cd('tests/unit'):
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
            assert any(s.test.run_tests_once())

def test44():
    with s.shell.tempdir():
        s.shell.run('mkdir .git')
        with s.shell.cd('tests/unit'):
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
            assert not any(s.test.run_tests_once())


def test6():
    with s.shell.tempdir():
        path = os.getcwd()
        s.shell.run('mkdir .git')
        with s.shell.cd('a/b/c'):
            assert path == s.fn.thread(
                s.test._climb(),
                s.test._git_root,
            )


def test5():
    val = [['tests/unit', [], ['test1.py', 'test2.py']],
           ['module', [], ['__init__.py']]]
    assert s.test._filter_test_files(val) == ['tests/unit/test1.py', 'tests/unit/test2.py']

def test55():
    val = [['/tmp/tdHuDDvMYt/tests/unit', [], ['test.py']],
           ['/tmp/tdHuDDvMYt/tests', ['unit'], []],
           ['/tmp/tdHuDDvMYt', ['.git', 'tests'], []]]
    assert s.test._filter_test_files(val) == ['tests/unit/test.py']
