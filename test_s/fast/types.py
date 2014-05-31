import s


def setup_module():
    s.log.setup(level='debug', short=True)


def test_list_remove_empties3():
    assert s.types._list_remove_empties([[]]) == [[]]


def test_heterogenous_list():
    assert s.types.parse(['a', 1]) == [str, int]


def test_homogenous_list():
    assert s.types.parse(['a']) == [str]


def test_list_repeat():
    assert s.types.parse([['asdf'],
                          ['asdf']]) == [[str]]


def test_list_repeat_with_empty():
    assert s.types.parse([[],
                          ['asdf']]) == [[str]]


def test_list_repeat_pattern():
    assert s.types.parse([['asdf', ['asdf'], ['asdf']],
                          ['asdf', ['asdf'], ['asdf']]]) == [[str, [str], [str]]]


def test_list_multiple_patters():
    assert s.types.parse([['asdf', ['asdf'], ['asdf']],
                          [1, 'asdf', ['asdf'], ['asdf']],
                          [1, 'asdf', ['asdf'], ['asdf']]]) == [[str, [str], [str]],
                                                                [int, str, [str], [str]]]


def test_tuples_repeats_uneven():
    assert s.types.parse(((1, 2), (1,), ())) == ((int,),)


def test_tuples_repeats():
    assert s.types.parse(((1, 2), (1, 3), ())) == ((int,),)


def test_tuples():
    assert s.types.parse((1, 'asdf')) == (int, str)


def test_list_fill_empties():
    assert s.types.parse([['asdf', ['asdf'], []],
                          ['asdf', ['asdf'], ['asdf']],]) == [[str, [str], [str]]]


def test_list_repeats():
    assert s.types.parse(['asdf', 'asdf', 'asdf']) == [str]


def test_list_heterogenous_repeats():
    assert s.types.parse(['asdf', 'asdf', 'asdf', 1]) == [str, int]


def test_list_nested_repeats():
    assert s.types.parse([['asdf', 'asdf', 'asdf']]) == [[str]]


def test_list_heterogenous_pattern():
    assert s.types.parse([['asdf', ['asdf', 'asdf', 'asdf'], ['asdf']],
                          ['asdf', ['asdf'], ['asdf', 'asdf', 'asdf']]]) == [[str, [str], [str]]]
