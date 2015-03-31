from __future__ import print_function, absolute_import
import s.colors
import s.strings
import pytest


def test_color():
    assert s.colors.red('foo') == s.strings.color('$red(foo)')


def test_indent():
    assert s.strings.indent('a\nb', 2) == '  a\n  b'


def test_unindent():
    assert s.strings.unindent('  a\n  b', 2) == 'a\nb'
    assert s.strings.unindent('  a\n  b', 0) == '  a\n  b'
    with pytest.raises(AssertionError):
        s.strings.unindent('  a\n  b', 3) == 'a\nb'
