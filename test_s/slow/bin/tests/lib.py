import os
import s
import sys
import s.bin.tests.lib


_keys = list(sys.modules.keys())


def setup_function(fn):
    s.log.setup.clear_cache()
    fn.tempdir_context = s.shell.tempdir()
    fn.tempdir_context.__enter__()
    for k, v in list(sys.modules.items()):
        if k not in _keys:
            del sys.modules[k]
    sys.path.insert(0, os.getcwd())


def teardown_function(fn):
    fn.tempdir_context.__exit__(None, None, None)
    sys.path.pop(0)


def test__collect_tests():
    with open('foo.py', 'w') as f:
        f.write('def test1():\n'
                '    pass')
    assert s.bin.tests.lib._collect_tests('foo.py') == ("<Function 'test1'>",)


def test_climb():
    s.shell.run('mkdir -p 1/2/3')
    s.shell.run('touch 1/a 1/2/b 1/2/3/c')
    x = os.getcwd()
    with s.shell.cd('1/2/3'):
        assert s.shell.climb()[:3] == [[os.path.join(x, '1/2/3'), [], ['c']],
                                       [os.path.join(x, '1/2'), ['3'], ['b']],
                                       [os.path.join(x, '1'), ['2'], ['a']]]


def test_fast_test_files():
    s.shell.run('mkdir -p .git test_foo/fast foo')
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py test_foo/fast/bar.py foo/bar.py foo/__init__.py')
    assert s.bin.tests.lib.fast_test_files() == (os.path.abspath('test_foo/fast/__init__.py'),
                                                 os.path.abspath('test_foo/fast/bar.py'))


def test_code_files():
    s.shell.run('mkdir -p .git foo')
    s.shell.run('touch foo/bar.py foo/__init__.py')
    assert s.bin.tests.lib.code_files() == (os.path.abspath('foo/__init__.py'),
                                            os.path.abspath('foo/bar.py'))


def test__python_packages():
    s.shell.run('mkdir -p .git foo')
    s.shell.run('touch foo/bar.py foo/__init__.py')
    assert s.bin.tests.lib._python_packages(s.shell.walk()) == (os.path.abspath('foo'),)


def test_one_result_per_test__test():
    with open('test_foo.py', 'w') as f:
        f.write('def test1():\n'
                '    pass\n'
                'def test2():\n'
                '    pass')
    assert len(s.bin.tests.lib._test('test_foo.py')) == 2


def test_import_syntax_error__test():
    with open('test_foo.py', 'w') as f:
        f.write('def test1():\n'
                'pass')
    val = s.bin.tests.lib._test('test_foo.py')
    assert 'IndentationError: expected an indented block' in val[0]['result']


def test_pytest_insight__test():
    with open('test_foo.py', 'w') as f:
        f.write('def test1():\n'
                '    x, y = 1, 3\n'
                '    assert x == y')
    val = s.bin.tests.lib._test('test_foo.py')
    assert 'assert 1 == 3' in val[0]['result']


def test_pass__test():
    with open('test_foo.py', 'w') as f:
        f.write('def test1():\n'
                '   x, y = 1, 1\n'
                '   assert x == y')
    val = s.bin.tests.lib._test('test_foo.py')
    assert not val[0]['result']


def test_one_pass_one_fail_run_lightweight_tests_once():
    s.shell.run('mkdir .git')
    with s.shell.cd('test_foo/fast'):
        with open('test1.py', 'w') as f:
            f.write('def test1():\n'
                    '    pass')
        with open('test2.py', 'w') as f:
            f.write('def test2():\n'
                    '    1/0')
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py')
    val = s.bin.tests.lib.light()
    assert len(val) == 3
    assert len([x for x in val if x[0]['result']]) == 1


def test_two_pass_run_lightweight_tests_once():
    s.shell.run('mkdir .git')
    with s.shell.cd('test_foo/fast'):
        with open('test1.py', 'w') as f:
            f.write('def test1():\n'
                    '    pass')
        with open('test2.py', 'w') as f:
            f.write('def test2():\n'
                    '    pass')
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py')
    assert [x[0]['result'] for x in s.bin.tests.lib.light()] == [None, False, False]


def test_climb_git_root():
    path = os.getcwd()
    s.shell.run('mkdir .git')
    with s.shell.cd('a/b/c'):
        assert path == s.func.pipe(
            s.shell.climb(),
            s.bin.tests.lib._git_root,
        )


def test_test_file():
    s.shell.run('mkdir -p test_foo/fast foo')
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py test_foo/fast/bar.py foo/bar.py foo/__init__.py')
    code_file = os.path.abspath('foo/bar.py')
    test_file = os.path.abspath('test_foo/fast/bar.py')
    assert s.bin.tests.lib.test_file(code_file) == test_file


def test_code_file():
    s.shell.run('mkdir -p test_foo/fast foo')
    s.shell.run('touch test_foo/__init__.py test_foo/fast/__init__.py test_foo/fast/bar.py foo/bar.py foo/__init__.py')
    code_file = os.path.abspath('foo/bar.py')
    test_file = os.path.abspath('test_foo/fast/bar.py')
    assert s.bin.tests.lib.code_file(test_file) == code_file
