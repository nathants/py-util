import os
import s


def test_collect_tests():
    with s.shell.tempdir():
        s.shell.run('mkdir -p .git tests/unit')
        with open('tests/unit/test_foo.py', 'w') as _file:
            _file.write("""def test1(): pass""")
        assert s.test._collect_tests('tests/unit/test_foo.py') == ["<Function 'test1'>"]


def test_climb():
    with s.shell.tempdir():
        s.shell.run('mkdir -p 1/2/3 && touch 1/a 1/2/b 1/2/3/s')
        x = os.getcwd()
        with s.shell.cd('1/2/3'):
            assert list(s.test._climb())[0] == [os.path.join(x, '1/2/3'), [], ['s']]
            assert list(s.test._climb())[1] == [os.path.join(x, '1/2'), ['3'], ['b']]
            assert list(s.test._climb())[2] == [os.path.join(x, '1'), ['2'], ['a']]

def test_all_test_files():
    with s.shell.tempdir():
        s.shell.run('mkdir -p .git tests/unit foo && touch tests/unit/test-foo-bar.py foo/bar.py foo/__init__.py')
        os.chdir('tests/unit')
        assert s.test.all_test_files() == ['tests/unit/test-foo-bar.py']


def test_all_code_files():
    with s.shell.tempdir():
        s.shell.run('mkdir -p .git foo && touch foo/bar.py foo/__init__.py')
        assert s.test._python_packages(os.walk('.')) == ['foo']
        assert set(s.test.all_code_files()) == {'foo/bar.py', 'foo/__init__.py'}


def test_test_fail():
    with s.shell.tempdir():
        with open('test.py', 'w') as io:
            io.write("""
def test1():
   x, y = 1, 2
   assert x == y
""")
        assert s.test._test('test.py')

def test_test_pass():
    with s.shell.tempdir():
        with open('test.py', 'w') as io:
            io.write("""
def test1():
   x, y = 1, 1
   assert x == y
""")
        assert not s.test._test('test.py')


def test_climb_and_test_fail():
    with s.shell.tempdir():
        with open('test.py', 'w') as fio:
            fio.write("""
def test1():
   x, y = 1, 2
   assert x == y
""")
        assert s.test.climb_and_test('test.py')


def test_climb_and_test_pass():
    with s.shell.tempdir():
        with open('test.py', 'w') as fio:
            fio.write("""
def test1():
   x, y = 1, 1
   assert x == y
""")
        assert not s.test.climb_and_test('test.py')


def test_climb_find_abspath():
    with s.shell.tempdir():
        s.shell.run('mkdir -p a/b/c && touch file')
        path = os.path.abspath('file')
        with s.shell.cd('a/b/c'):
            assert path == s.test._climb_find_abspath('file')


def test_run_tests_once_fail():
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
            val = s.test.run_tests_once()
            assert len(val) == 2
            assert len([x for x in val if x]) == 1


def test_run_tests_once_pass():
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
            assert s.test.run_tests_once() == [False, False]


def test_climb_git_root():
    with s.shell.tempdir():
        path = os.getcwd()
        s.shell.run('mkdir .git')
        with s.shell.cd('a/b/c'):
            assert path == s.fn.thread(
                s.test._climb(),
                s.test._git_root,
            )
