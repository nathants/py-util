import s
import pytest


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


def test_dict_single():
    assert s.types.parse({'asdf': False}) == {str: bool}


def test_dict_double():
    assert s.types.parse({'asdf': False, 1: 1.0}) == {str: bool, int: float}


def test_list_of_dict_repeats():
    assert s.types.parse([{'1': False},
                          {'2': False}]) == [{str: bool}]


def test_list_of_dict():
    assert s.types.parse(['a', {1: 'asdf'}]) == [str, {int: str}]


def test_dict_duplicate_keys():
    assert s.types.parse({2: 1.1, 3: 2.2, 1: False}) == {(int, 0): bool, (int, 1): float}


def test_dict_duplicate_keys_ordering():
    assert s.types.parse({1: False, 2: None}) == {(int,0): bool, (int,1): type(None)}


def test_dict_matching_duplicates():
    assert s.types.parse({'1': 1,
                          '2': 1}) == {str: int}


def test_dict_dict_of_patterns():
    assert s.types.parse({False: [['asdf', ['asdf'], []],
                                  ['asdf', ['asdf'], ['asdf']]]}) == {bool: [[str, [str], [str]]]}


def test_set():
    assert s.types.parse({1, 2.0}) == {int, float}


def test_frozen_set():
    assert s.types.parse(frozenset([1])) == {int}
