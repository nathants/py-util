from __future__ import print_function, absolute_import
import re
import pprint
import s
import types
import uuid


default = str(uuid.uuid4()) # sentinel used to signal default values


def validate(schema, value):
    """
    >>> import pytest

    # simple values represent themselves
    >>> assert validate(123, 123) == 123
    >>> with pytest.raises(ValueError):
    ...     validate(123, '123')

    # lists represent variable length homogenous lists/tuples
    >>> assert validate([int], [1, 2]) == [1, 2]
    >>> with pytest.raises(ValueError):
    ...     validate([int], [1, '2'])

    # tuples represent fixed length heterogenous lists/tuples
    >>> assert validate((int, int), [1, 2]) == [1, 2]
    >>> with pytest.raises(ValueError):
    ...     validate((int, int), [1])

    # dicts can use types and values for k's and v's, and also lambdas for v's.

    # dicts with types->types
    >>> assert validate({int: str}, {1: '2', 3: '4'}) == {1: '2', 3: '4'}
    >>> with pytest.raises(ValueError):
    ...     validate({int: str}, {1: '2', 3: 4.0})

    # dicts with types->values
    >>> assert validate({int: str, 'name': str}, {1: '2', 'name': 'bob'}) == {1: '2', 'name': 'bob'}

    # dicts with complex validation
    >>> assert validate({'name': lambda x: x in ['john', 'jane']}, {'name': 'jane'}) == {'name': 'jane'}
    >>> with pytest.raises(ValueError):
    ...     validate({'name': lambda x: x in ['john', 'jane']}, {'name': 'rose'})

    # dicts with optional k's, that provide a value for a missing key and validate provided keys
    >>> schema = {'name': lambda x: x == default and 'jane' or isinstance(x, str)}
    >>> assert validate(schema, {}) == {'name': 'jane'}
    >>> assert validate(schema, {'name': 'rose'}) == {'name': 'rose'}
    >>> with pytest.raises(ValueError):
    ...     validate(schema, {'name': 123})

    # validate is recursive, so nest schemas freely
    >>> schema = {'users': [{'name': (str, str), 'id': int}]}
    >>> obj = {'users': [{'name': ('jane', 'smith'), 'id': 85},
    ...                  {'name': ('john', 'smith'), 'id': 93}]}
    >>> assert validate(schema, obj) == obj
    >>> with pytest.raises(ValueError):
    ...     validate(schema, {'users': [{'name': ('jane', 'e', 'smith'), 'id': 85}]})

    """
    try:
        if isinstance(schema, dict):
            assert isinstance(value, dict), 'value {}, should be a dict for schema: {}'.format(value, schema)
            for k, v in value.items():
                value_mismatch = k not in schema
                type_mismatch = type(k) not in [x for x in schema if isinstance(x, type)]
                if value_mismatch and type_mismatch:
                    raise ValueError('key: {} <{}>, does not match schema keys: {}'.format(k, type(k), schema.keys()))
                else:
                    _validate(schema[type(k)] if value_mismatch else schema[k], v)
            for k, v in schema.items():
                if k not in value and isinstance(v, types.LambdaType):
                    value = s.dicts.merge(value, {k: v(default)})

        else:
            _validate(schema, value)
        return value
    except ValueError as e:
        raise ValueError(_prettify(
            'failed to validate obj against schema\n--obj--\n{}\n--schema--\n{}\n--details--\n{}'.format(
                pprint.pformat(value, width=1),
                pprint.pformat(schema, width=1),
                getattr(e, 'message', '\n').splitlines()[-1],
            )
        ))


def _validate(validator, value):
    if isinstance(validator, (list, tuple)):
        if not isinstance(value, (list, tuple)):
            raise ValueError('{} <{}> is not a {}'.format(value, type(value), validator))
        elif isinstance(validator, list):
            if len(validator) != 1:
                raise ValueError('list validators represent variable length iterables and must contain a single validator: {}'.format(validator)) # noqa
            for v in value:
                _validate(validator[0], v)
        elif isinstance(validator, tuple):
            if len(validator) != len(value):
                raise ValueError('{} <{}> mismatched length of validator {}'.format(value, type(value), validator))
            for _validator, _val in zip(validator, value):
                _validate(_validator, _val)
    elif isinstance(validator, dict):
        if not isinstance(value, dict):
            raise ValueError('{} <{}> does not match schema {}'.format(value, type(value), validator))
        validate(validator, value)
    elif isinstance(validator, type):
        if type(value) is not validator:
            raise ValueError('{} <{}> is not a {}'.format(value, type(value), validator))
    elif isinstance(validator, types.FunctionType):
        if not validator(value):
            raise ValueError('{} <{}> failed validator {}'.format(value, type(value), s.func.source(validator)))
    elif value != validator:
        raise ValueError('{} <{}> != {}'.format(value, type(value), validator))


def _prettify(x):
    return re.sub("\<type \'(\w+)\'\>", r'\1', x)
