from __future__ import print_function, absolute_import
import s
import types
import uuid


default = str(uuid.uuid4()) # sentinel used to signal default values


def validate(schema, value):
    """
    >>> import pytest

    lists represent variable length homogenous lists/tuples

    >>> validate([int], [1, 2])
    [1, 2]
    >>> with pytest.raises(ValueError):
    ...     validate([int], [1, '2'])

    tuples represent fixed length heterogenous lists/tuples

    >>> validate((int, int), [1, 2])
    [1, 2]
    >>> with pytest.raises(ValueError):
    ...     validate((int, int), [1])
    """
    if isinstance(schema, dict):
        assert isinstance(value, dict), 'value {}, should be a dict for schema: {}'.format(value, schema)
        for k, v in value.items():
            value_mismatch = k not in schema
            type_mismatch = type(k) not in [x for x in schema if isinstance(x, type)]
            if value_mismatch and type_mismatch:
                raise ValueError('key: {} ({}), does not match schema keys: {}'.format(k, type(k), schema.keys()))
            else:
                _validate(schema[type(k)] if value_mismatch else schema[k], v)
        for k, v in schema.items():
            if k not in value and isinstance(v, types.LambdaType):
                value = s.dicts.merge(value, {k: v(default)})

    else:
        _validate(schema, value)
    return value


def _validate(validator, value):
    if isinstance(validator, (list, tuple)):
        if not isinstance(value, (list, tuple)):
            raise ValueError('{} ({}) is not a {}'.format(value, type(value), validator))
        elif isinstance(validator, list):
            if len(validator) != 1:
                raise ValueError('list validators represent variable length iterables and must contain a single validator: {}'.format(validator)) # noqa
            for v in value:
                _validate(validator[0], v)
        elif isinstance(validator, tuple):
            if len(validator) != len(value):
                raise ValueError('{} ({}) mismatched length of validator {}'.format(value, type(value), validator))
            for _validator, _val in zip(validator, value):
                _validate(_validator, _val)
    elif isinstance(validator, dict):
        if not isinstance(value, dict):
            raise ValueError('{} ({}) does not match schema {}'.format(value, type(value), validator))
        validate(validator, value)
    elif isinstance(validator, type):
        if type(value) is not validator:
            raise ValueError('{} ({}) is not a {}'.format(value, type(value), validator))
    elif isinstance(validator, types.FunctionType):
        if not validator(value):
            raise ValueError('{} ({}) failed validator {}'.format(value, type(value), s.func.source(validator)))
    elif value != validator:
        raise ValueError('{} ({}) != {}'.format(value, type(value), validator))
