import s.bin.tests.lib
import os


def test_python_packages():
    data = [['/foo', ['bar'], []],
            ['/foo/bar', ['asdf'], ['__init__.py']],
            ['/foo/bar/asdf', [], ['__init__.py']]]
    assert s.bin.tests.lib._python_packages(data) == ('/foo/bar',)


def test_nested__test_file():
    assert s.bin.tests.lib._test_file('foo/bin/bar.py') == 'test_foo/fast/bin/bar.py'


def test_nested__code_file():
    assert s.bin.tests.lib._code_file('test_foo/fast/bin/bar.py') == 'foo/bin/bar.py'


def test__test_file():
    assert s.bin.tests.lib._test_file('foo/bar.py') == 'test_foo/fast/bar.py'


def test__code_file():
    assert s.bin.tests.lib._code_file('test_foo/fast/bar.py') == 'foo/bar.py'


def test_handles_init__test_file():
    assert s.bin.tests.lib._test_file('foo/__init__.py') == 'test_foo/fast/__init__.py'


def test_handles_init__code_file():
    assert s.bin.tests.lib._code_file(s.bin.tests.lib._test_file('foo/__init__.py')) == 'foo/__init__.py'


def test__filter_test_files():
    val = [['test_module', ['fast'], ['__init__.py']],
           ['test_module/fast', [], ['__init__.py', 'test1.py', 'test1.pyc', 'test2.py', '.#test2.py', 'test2_flymake.py']],
           ['module', [], ['__init__.py']]]
    assert s.bin.tests.lib._filter_test_files(val) == tuple([os.path.join('test_module/fast', x)
                                                             for x in ['__init__.py', 'test1.py', 'test2.py']])


def test__parse_coverage():
    text = 's/cached      29     22    24%   15-23, 27-41'
    assert s.bin.tests.lib._parse_coverage('s.cached', text) == {'name': 's.cached', 'percent': '24', 'missing': ('15-23', '27-41')}


def test_single_missing__parse_coverage():
    text = 's/cached      29     22    24%   27-41'
    assert s.bin.tests.lib._parse_coverage('s.cached', text) == {'name': 's.cached', 'percent': '24', 'missing': ('27-41',)}


def test_no_missing__parse_coverage():
    text = 's/cached      29     22    24%   '
    assert s.bin.tests.lib._parse_coverage('s.cached', text) == {'name': 's.cached', 'percent': '24', 'missing': ()}


def test_init__parse_coverage():
    text = ('s/__init__      29     22    24%   \n'
            's/foo__init__      29     22    24%   \n')
    assert s.bin.tests.lib._parse_coverage('s', text) == {'name': 's', 'percent': '24', 'missing': ()}
