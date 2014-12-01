from __future__ import print_function, absolute_import
import s
import pytest
import six


def test_validate_returns_value():
    assert s.schema.validate(int, 123) == 123


def test_unicde_synonymous_with_str():
    assert s.schema.validate(str, u'asdf') == 'asdf'
    assert s.schema.validate(dict, {u'a': 'b'}) == {'a': 'b'}


def test_dicts_must_have_str_keys():
    schema = {object: object}
    assert s.schema.validate({str: str}, {'a': 'b'}) == {'a': 'b'}
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: 2})


def test_bytes_matches_str_schemas():
    schema = 'asdf'
    s.schema.validate(schema, b'asdf')


def test_partial_comparisons_for_testing():
    schema = {'blah': str,
              'data': [{str: str}]}
    data = {'blah': 'foobar',
            'data': [{'a': 'b'},
                     {'c': 'd'},
                     # ...
                     # pretend 'data' is something too large to specify as a value literal in a test
                     ]}
    s.schema.validate(schema, data)
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'blah': 'foobar',
                                   'data': [{'a': 1}]})


def test_object_dict():
    schema = {object: object}
    s.schema.validate(schema, {'1': 2})


def test_object_tuple():
    schema = (object, object)
    s.schema.validate(schema, (1, '2'))
    with pytest.raises(AssertionError):
        s.schema.validate(schema, (1, 2, 3))


def test_object_list():
    schema = [object]
    s.schema.validate(schema, [1, 2, 3])
    s.schema.validate(schema, [1, '2', 3.0])


def test_test_annotations_return():
    if six.PY3:
        def fn():
            return 123
        fn.__annotations__ = {'return': str}
        fn = s.schema.check(fn)
        with pytest.raises(AssertionError):
            fn()


def test_annotation_args():
    if six.PY3:
        def fn(x):
            return str(x)
        fn.__annotations__ = {'x': int, 'return': str}
        fn = s.schema.check(fn)
        assert fn(1) == '1'
        with pytest.raises(AssertionError):
            fn(1.0)


def test_annotation_kwargs():
    if six.PY3:
        def fn(x=0):
            return str(x)
        fn.__annotations__ = {'x': int, 'return': str}
        fn = s.schema.check(fn)
        assert fn(x=1) == '1'
        with pytest.raises(AssertionError):
            fn(x=1.0)


def test_check_args_and_kwargs():
    @s.schema.check(int, b=float, returns=str)
    def fn(a, b=0):
        return str(a + b)
    assert fn(1) == '1'
    assert fn(1, b=.5) == '1.5'
    with pytest.raises(AssertionError):
        fn(1, 1)
    with pytest.raises(AssertionError):
        fn(1.0)
    with pytest.raises(AssertionError):
        fn(1, b='2')
    with pytest.raises(AssertionError):
        fn(1, c='2')


def test_check_returns():
    @s.schema.check(returns=str)
    def badfn():
        return 0
    with pytest.raises(AssertionError):
        badfn()


def test_object_type():
    schema = {str: object}
    s.schema.validate(schema, {'a': 'apple'})
    s.schema.validate(schema, {'b': 'banana'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: 'apple'})


def test_type_to_lambda():
    schema = {str: lambda x: x == 'apple'}
    s.schema.validate(schema, {'a': 'apple'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'notapple'})


def test_optional_cannot_return_default():
    schema = {'a': lambda x: s.schema.default}
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {})


def test_required_type_to_type():
    schema = {'a': 'apple',
              str: float}
    s.schema.validate(schema, {'a': 'apple', '1': 1.1})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple'})


def test_required_value_to_type():
    schema = {'a': 'apple',
              'b': str}
    s.schema.validate(schema, {'a': 'apple', 'b': 'banana'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple', 'b': 1})


def test_required_value_to_value():
    schema = {'a': 'apple',
              'b': 'banana'}
    s.schema.validate(schema, {'a': 'apple', 'b': 'banana'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple'})


def test_required_type_to_value():
    schema = {'a': 'apple',
              str: 'banana'}
    s.schema.validate(schema, {'a': 'apple', 'b': 'banana'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple', 1: 'banana'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple', 'b': 'notbanana'})


def test_type_to_value():
    schema = {str: 'apple'}
    s.schema.validate(schema, {'a': 'apple'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'notapple'})


def test_optional_value_key_with_validation():
    schema = {'a': 'apple',
              'b': lambda x: x == s.schema.default and 'banana' or x == 'banana'}
    s.schema.validate(schema, {'a': 'apple'}) == {'a': 'apple', 'b': 'banana'}
    s.schema.validate(schema, {'a': 'apple', 'b': 'banana'}) == {'a': 'apple', 'b': 'banana'}
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'a': 'apple', 'b': 'notbanana'})


def test_value_schema():
    schema = 1
    s.schema.validate(schema, 1)
    with pytest.raises(AssertionError):
        s.schema.validate(schema, 2)


def test_single_type_schema():
    schema = int
    s.schema.validate(schema, 1)
    with pytest.raises(AssertionError):
        s.schema.validate(schema, '1')


def test_single_iterable_length_n():
    schema = [int]
    s.schema.validate(schema, [1, 2])
    with pytest.raises(AssertionError):
        s.schema.validate(schema, [1, '2'])


def test_single_iterable_fixed_length():
    schema = (float, int)
    s.schema.validate(schema, [1.1, 2])
    with pytest.raises(AssertionError):
        s.schema.validate(schema, [1.1, '2'])


def test_nested_type_to_type_mismatch():
    schema = {str: {str: int}}
    s.schema.validate(schema, {'1': {'1': 1}})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'1': None})


def test_nested_type_to_type():
    schema = {str: {str: int}}
    s.schema.validate(schema, {'1': {'1': 1}})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'1': {'1': '1'}})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'1': {1: 1}})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: {'1': 1}})


def test_type_to_type():
    schema = {str: int}
    s.schema.validate(schema, {'1': 1})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: 1})


def test_value_to_type():
    schema = {'foo': int}
    s.schema.validate(schema, {'foo': 1})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'foo': 'bar'})


def test_value_to_value():
    schema = {'foo': 'bar'}
    s.schema.validate(schema, {'foo': 'bar'})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'foo': 1})


def test_value_to_validator():
    schema = {'foo': lambda x: isinstance(x, int) and x > 0}
    s.schema.validate(schema, {'foo': 1})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'foo': 0})


def test_nested_value_to_validator():
    schema = {'foo': {'bar': lambda x: isinstance(x, int) and x > 0}}
    s.schema.validate(schema, {'foo': {'bar': 1}})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'foo': {'bar': 0}})


def test_iterable_length_n_bad_validator():
    schema = {str: [str, str]}
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'blah': ['blah', 'blah']})


def test_iterable_length_n():
    schema = {str: [str]}
    s.schema.validate(schema, {'1': ['1', '2']})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: 1})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: ['1', 2]})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'1': None})


def test_iterable_fixed_length():
    schema = {str: (str, str)}
    s.schema.validate(schema, {'1': ['1', '2']})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: ['1']})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: ['1', '2', '3']})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {1: ['1', 2]})


def test_nested_iterables():
    schema = {str: [[str]]}
    s.schema.validate(schema, {'1': [['1'], ['2']]})
    with pytest.raises(AssertionError):
        assert s.schema.validate(schema, {'1': [['1'], [1]]})


def test_many_keys():
    schema = {str: int}
    s.schema.validate(schema, {'1': 2, '3': 4})
    with pytest.raises(AssertionError):
        s.schema.validate(schema, {'1': 2, '3': 4.0})


def test_value_matches_are_higher_precedence_than_type_matches():
    schema = {str: int,
              'foo': 'bar'}
    s.schema.validate(schema, {'1': 2, 'foo': 'bar'})
    with pytest.raises(AssertionError):
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
    s.schema.validate(schema, data)
    with pytest.raises(AssertionError):
        s.schema.validate(schema, s.dicts.merge(data, {'name': 123}))
    with pytest.raises(AssertionError):
        s.schema.validate(schema, s.dicts.merge(data, {'events': [None]}))
    with pytest.raises(AssertionError):
        s.schema.validate(schema, s.dicts.merge(data, {'events': [None] + data['events']}))
    with pytest.raises(AssertionError):
        s.schema.validate(schema, s.dicts.merge(data, {'events': [{'what': 'shopping',
                                                                   'when': 123.11,
                                                                   'where': [0]}]}))
