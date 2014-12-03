from __future__ import print_function, absolute_import
import six
import functools
import re
import pprint
import s
import types
import uuid
import inspect


default = str(uuid.uuid4()) # sentinel used to signal default values


def is_valid(schema, value):
    try:
        validate(schema, value)
        return True
    except AssertionError:
        return False


def validate(schema, value):
    """
    >>> import pytest

    ### basic usage

    # simple values represent themselves
    >>> schema = int
    >>> validate(schema, 123)
    123
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, '123')

    # lists represent variable length homogenous lists/tuples
    >>> schema = [int]
    >>> validate(schema, [1, 2])
    [1, 2]
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, [1, '2'])

    # tuples represent fixed length heterogenous lists/tuples
    >>> schema = (int, int)
    >>> validate(schema, [1, 2])
    [1, 2]
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, [1])

    ### dicts can use types and values for k's and v's, and also lambdas for v's.

    # dicts with types->types
    >>> schema = {str: int}
    >>> validate(schema, {'1': 2})
    {'1': 2}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'1': 2.0})

    # dicts with types->values. fyi, the only type allowed for keys is "str".
    >>> schema = {str: 'bob'}
    >>> validate(schema, {'alias': 'bob'})
    {'alias': 'bob'}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'alias': 'joe'})


    # dicts with values->types
    >>> schema = {'name': float}
    >>> validate(schema, {'name': 3.14})
    {'name': 3.14}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'alias': 3.14})

    # dicts with complex validation
    >>> validate({'name': lambda x: x in ['john', 'jane']}, {'name': 'jane'})
    {'name': 'jane'}
    >>> with pytest.raises(AssertionError):
    ...     validate({'name': lambda x: x in ['john', 'jane']}, {'name': 'rose'})

    # dicts with optional k's provide a value for a missing key and validate provided keys
    >>> schema = {'name': lambda x: x == default and 'jane' or isinstance(x, str)}
    >>> validate(schema, {})
    {'name': 'jane'}
    >>> validate(schema, {'name': 'rose'})
    {'name': 'rose'}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'name': 123})

    # validate is recursive, so nest schemas freely
    >>> schema = {'users': [{'name': (str, str), 'id': int}]}
    >>> obj = {'users': [{'name': ('jane', 'smith'), 'id': 85},
    ...                  {'name': ('john', 'smith'), 'id': 93}]}
    >>> assert validate(schema, obj) == obj
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'users': [{'name': ('jane', 'e', 'smith'), 'id': 85}]})

    ### schema based pattern matching

    # # with a combination of values and object, we can express complex assertions on data
    # while True:
    #     msg = socket.recv()
    #     if validate([":order", {'sender': str, 'instructions': [str]], msg):
    #         key, val = msg
    #         run_order(val)
    #     elif validate([":shutdown", object]):
    #         sys.exit(1)
    #     else:
    #         print('unknown message')
    #

    """
    try:
        if isinstance(schema, dict):
            assert isinstance(value, dict), 'value {} <{}> should be a dict for schema: {} <{}>'.format(value, type(value), schema, type(schema))
            for k in value.keys():
                assert isinstance(k, s.data.string_types), 'dict keys must be str: {}, {}'.format(k, value)
            validated_schema_items = _check_for_items_in_value_that_dont_satisfy_schema(schema, value)
            value = _check_for_items_in_schema_missing_in_value(schema, value, validated_schema_items)
        else:
            _check(schema, value)
        return value
    except AssertionError as e:
        s.exceptions.update(e, lambda x: _prettify(x + _helpful_message(schema, value)))
        raise


def _check_for_items_in_value_that_dont_satisfy_schema(schema, value):
    validated_schema_items = []
    for k, v in value.items():
        value_mismatch = k not in schema
        type_mismatch = type(k) not in [x for x in schema if isinstance(x, type)] and object not in schema
        assert not value_mismatch or not type_mismatch, '{} <{}> does not match schema keys: {}'.format(k, type(k), ', '.join(['{} <{}>'.format(x, type(x)) for x in schema.keys()]))
        key = type(k) if value_mismatch else k
        validator = schema.get(key, schema.get(object))
        validated_schema_items.append((key, validator))
        _check(validator, v)
    return validated_schema_items


def _check_for_items_in_schema_missing_in_value(schema, value, validated_schema_items):
    for k, v in schema.items():
        if k not in value and (k, v) not in validated_schema_items: # only check schema items if they haven't already been satisfied
            if type(k) is type: # if a type key is missing, look for an item that satisfies it
                for vk, vv in value.items():
                    with s.exceptions.ignore(AssertionError):
                        validate(k, vk)
                        validate(v, vv)
                        break
                else:
                    raise AssertionError('{} <{}> is missing (key, value) pair: {} <{}>, {} <{}>'.format(value, type(value), k, type(k), v, type(v)))
            else: # if a value key is missing, it must be optional or its a required key violation
                assert isinstance(v, types.FunctionType), '{} <{}> is missing required key: {} <{}>'.format(value, type(value), k, type(k))
                val = v(default)
                assert val != default, 'you accidentally return s.schema.default instead of your actual default value for: {}, {}'.format(k, v)
                value = s.dicts.merge(value, {k: val})
    return value


def _check(validator, value):
    assert not isinstance(validator, set), 'a set cannot be a validator: {}'.format(validator)
    if validator is object:
        return value
    elif isinstance(validator, (list, tuple)):
        assert isinstance(value, (list, tuple)), '{} <{}> is not a {} <{}>'.format(value, type(value), validator, type(validator))
        if isinstance(validator, list):
            assert len(validator) == 1, 'list validators represent variable length iterables and must contain a single validator: {}'.format(validator)
            for v in value:
                _check(validator[0], v)
        elif isinstance(validator, tuple):
            assert len(validator) == len(value), '{} <{}> mismatched length of validator {} <{}>'.format(value, type(value), validator, type(validator))
            for _validator, _val in zip(validator, value):
                _check(_validator, _val)
    elif isinstance(validator, dict):
        assert isinstance(value, dict), '{} <{}> does not match schema {} <{}>'.format(value, type(value), validator, type(validator))
        validate(validator, value)
    elif isinstance(validator, type):
        if type(value) in s.data.string_types:
            value = str()
        assert type(value) is validator, '{} <{}> is not a <{}>'.format(value, type(value), validator)
    elif isinstance(validator, types.FunctionType):
        assert validator(value), '{} <{}> failed validator {}'.format(value, type(value), s.func.source(validator))
    else:
        with s.exceptions.ignore(AttributeError):
            value = value.decode('utf-8')
        assert value == validator, '{} <{}> != {} <{}>'.format(value, type(value), validator, type(validator))


def _helpful_message(schema, value):
    for fn in [x for x in s.seqs.flatten(schema) if isinstance(x, types.FunctionType)]:
        try:
            filename, linenum = fn.func_code.co_filename, fn.func_code.co_firstlineno
            with open(filename) as _file:
                lines = _file.read().splitlines()
            start = end = None
            for i in reversed(range(linenum)):
                if not lines[i].strip() or 'def ' in lines[i] or 'class ' in lines[i]:
                    break
                elif ' = ' in lines[i]:
                    start = i
                    break
            if any(x in lines[start] for x in ['{', '(', '[']):
                for i in range(linenum, len(lines) + 1):
                    text = '\n'.join(lines[start:i])
                    if all(text.count(x) == text.count(y) for x, y in [('{', '}'), ('[', ']'), ('(', ')')]):
                        end = i
                        break
            if start is not None and end is not None:
                schema = '\n'.join(lines[start:end])
                size = len(lines[start]) - len(lines[start].lstrip())
                schema = s.strings.unindent(schema, size)
            break
        except:
            continue
    else:
        schema = pprint.pformat(schema, width=1)

    return '\n\n--obj--\n{}\n--schema--\n{}\n--end--'.format(
        pprint.pformat(value, width=1),
        schema,
    )


def _prettify(x):
    return re.sub("\<\w+ \'(\w+)\'\>", r'\1', str(x))


def get_schemas(arg_schemas, kwarg_schemas, fn):
    if not arg_schemas and not kwarg_schemas and six.PY3:
        sig = inspect.signature(fn)
        arg_schemas = [x.annotation for x in sig.parameters.values() if x.default is inspect._empty]
        kwarg_schemas = {x.name: x.annotation for x in sig.parameters.values() if x.default is not inspect._empty}
        if sig.return_annotation is not inspect._empty:
            kwarg_schemas['returns'] = sig.return_annotation
    assert arg_schemas or kwarg_schemas, 'you asked to check, but provided no schemas for: {}'.format(s.func.name(fn))
    return arg_schemas, kwarg_schemas


@s.hacks.optionally_parameterized_decorator
def check(*args, **kwargs):
    def decorator(fn):
        arg_schemas, kwarg_schemas = get_schemas(args, kwargs, fn)
        returns_schema = kwarg_schemas.pop('returns', lambda x: x)
        name = s.func.name(fn)
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            assert len(arg_schemas) == len(args), 'you asked to check {} for {} args, but {} were provided: {}'.format(name, len(arg_schemas), len(args), args)
            for key, value in kwargs.items():
                assert key in kwarg_schemas, 'cannot check {} for unknown key: {}={}'.format(name, key, value)
            try:
                args = [validate(schema, arg) for schema, arg in zip(arg_schemas, args)]
                checker = lambda k, v: validate(kwarg_schemas.get(k, lambda x: x), v)
                kwargs = dict((k, checker(k, v)) for k, v in kwargs.items())
                value = fn(*args, **kwargs)
                assert value is not None, 'you cannot return None from s.schema.check\'d function'
                return s.schema.validate(returns_schema, value)
            except AssertionError as e:
                s.exceptions.update(e, lambda x: x + '\n\n--function--\n{}\n--end--'.format(name))
                raise
        return decorated
    return decorator
