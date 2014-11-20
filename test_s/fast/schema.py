from __future__ import print_function, absolute_import
import s
import pytest


def test_optional_key():
    schema = {'a': 'apple',
              'b': lambda x: x == s.schema.default and 'banana' or x == 'banana'}
    assert s.schema.validate(schema, {'a': 'apple'}) == {'a': 'apple', 'b': 'banana'}
    assert s.schema.validate(schema, {'a': 'apple', 'b': 'banana'}) == {'a': 'apple', 'b': 'banana'}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'a': 'apple', 'b': 'notbanana'})


def test_value_schema():
    schema = 1
    assert s.schema.validate(schema, 1) == 1
    with pytest.raises(ValueError):
        s.schema.validate(schema, 2)


def test_single_type_schema():
    schema = int
    assert s.schema.validate(schema, 1) == 1
    with pytest.raises(ValueError):
        s.schema.validate(schema, '1')


def test_single_iterable_length_n():
    schema = [int]
    assert s.schema.validate(schema, [1, 2]) == [1, 2]
    with pytest.raises(ValueError):
        s.schema.validate(schema, [1, '2'])


def test_single_iterable_fixed_length():
    schema = (float, int)
    assert s.schema.validate(schema, [1.1, 2]) == [1.1, 2]
    with pytest.raises(ValueError):
        s.schema.validate(schema, [1.1, '2'])


def test_nested_type_to_type_mismatch():
    schema = {str: {float: int}}
    assert s.schema.validate(schema, {'1': {1.1: 1}}) == {'1': {1.1: 1}}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'1': None})


def test_nested_type_to_type():
    schema = {str: {float: int}}
    assert s.schema.validate(schema, {'1': {1.1: 1}}) == {'1': {1.1: 1}}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'1': {1.1: '1'}})
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'1': {1: 1}})
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: {1.1: 1}})


def test_type_to_type():
    schema = {str: int}
    assert s.schema.validate(schema, {'1': 1}) == {'1': 1}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: 1})


def test_value_to_type():
    schema = {'foo': int}
    assert s.schema.validate(schema, {'foo': 1}) == {'foo': 1}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'foo': 'bar'})


def test_value_to_value():
    schema = {'foo': 'bar'}
    assert s.schema.validate(schema, {'foo': 'bar'}) == {'foo': 'bar'}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'foo': 1})


def test_value_to_validator():
    schema = {'foo': lambda x: isinstance(x, int) and x > 0}
    assert s.schema.validate(schema, {'foo': 1}) == {'foo': 1}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'foo': 0})


def test_nested_value_to_validator():
    schema = {'foo': {'bar': lambda x: isinstance(x, int) and x > 0}}
    assert s.schema.validate(schema, {'foo': {'bar': 1}}) == {'foo': {'bar': 1}}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'foo': {'bar': 0}})


def test_iterable_length_n_bad_validator():
    schema = {str: [str, str]}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'blah': ['blah', 'blah']})


def test_iterable_length_n():
    schema = {str: [str]}
    assert s.schema.validate(schema, {'1': ['1', '2']}) == {'1': ['1', '2']}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: 1})
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: ['1', 2]})
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'1': None})


def test_iterable_fixed_length():
    schema = {str: (str, str)}
    assert s.schema.validate(schema, {'1': ['1', '2']}) == {'1': ['1', '2']}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: ['1']})
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: ['1', '2', '3']})
    with pytest.raises(ValueError):
        s.schema.validate(schema, {1: ['1', 2]})


def test_nested_iterables():
    schema = {str: [[str]]}
    assert s.schema.validate(schema, {'1': [['1'], ['2']]}) == {'1': [['1'], ['2']]}
    with pytest.raises(ValueError):
        assert s.schema.validate(schema, {'1': [['1'], [1]]})


def test_many_keys():
    schema = {str: int}
    assert s.schema.validate(schema, {'1': 2, '3': 4}) == {'1': 2, '3': 4}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'1': 2, '3': 4.0})


def test_value_matches_are_higher_precedence_than_type_matches():
    schema = {str: int,
              'foo': 'bar'}
    assert s.schema.validate(schema, {'1': 2, 'foo': 'bar'}) == {'1': 2, 'foo': 'bar'}
    with pytest.raises(ValueError):
        s.schema.validate(schema, {'1': 2, 'foo': 'asdf'})


def test_complex_types():
    schema = {'name': str,
              'age': lambda x: isinstance(x, int) and x > 0,
              'friends': [lambda x: isinstance(x, str) and len(x.split()) == 2],
              'events': [{'what': str,
                          'when': float,
                          'where': (int, int)}]}
    data = {'name': 'henry',
            'age': 99,
            'friends': ['dave g', 'tom p'],
            'events': [{'what': 'party',
                        'when': 123.11,
                        'where': (65, 73)},
                       {'what': 'shopping',
                        'when': 145.22,
                        'where': [77, 44]}]}
    assert s.schema.validate(schema, data) == data
    with pytest.raises(ValueError):
        s.schema.validate(schema, s.dicts.merge(data, {'name': 123}))
    with pytest.raises(ValueError):
        s.schema.validate(schema, s.dicts.merge(data, {'events': [None]}))
    with pytest.raises(ValueError):
        s.schema.validate(schema, s.dicts.merge(data, {'events': [None] + data['events']}))
    with pytest.raises(ValueError):
        s.schema.validate(schema, s.dicts.merge(data, {'events': [{'what': 'shopping',
                                                                   'when': 123.11,
                                                                   'where': [0]}]}))
