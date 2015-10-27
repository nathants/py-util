import util.colors
import util.strings
import pytest


def test_color():
    assert util.colors.red('foo') == util.strings.color('$red(foo)')


def test_indent():
    assert util.strings.indent('a\nb', 2) == '  a\n  b'


def test_unindent():
    assert util.strings.unindent('  a\n  b', 2) == 'a\nb'
    assert util.strings.unindent('  a\n  b', 0) == '  a\n  b'
    with pytest.raises(AssertionError):
        util.strings.unindent('  a\n  b', 3) == 'a\nb'
