import s


def test_color():
    assert s.colors.red('foo') == s.strings.color('$red(foo)')
