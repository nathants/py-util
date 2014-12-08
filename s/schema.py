from __future__ import print_function, absolute_import
import six
import functools
import re
import pprint
import s
import types
import inspect


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
    >>> assert validate(schema, 123) == 123
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, '123')

    # lists represent variable length homogenous lists/tuples
    >>> schema = [int]
    >>> assert validate(schema, [1, 2]) == [1, 2]
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, [1, '2'])

    # tuples represent fixed length heterogenous lists/tuples
    >>> schema = (int, int)
    >>> assert validate(schema, [1, 2]) == [1, 2]
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, [1])

    ### union types with :or
    >>> schema = (':or', int, float)
    >>> assert validate(schema, 1) == 1
    >>> assert validate(schema, 1.0) == 1.0
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, '1')

    ### dicts can use types and values for k's and v's, and also lambdas for v's.

    # dicts with types->types
    >>> schema = {str: int}
    >>> assert validate(schema, {'1': 2}) == {'1': 2}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'1': 2.0})

    # dicts with types->values. fyi, the only type allowed for keys is "str".
    >>> schema = {str: 'bob'}
    >>> assert validate(schema, {'alias': 'bob'}) == {'alias': 'bob'}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'alias': 'joe'})


    # dicts with values->types
    >>> schema = {'name': float}
    >>> assert validate(schema, {'name': 3.14}) == {'name': 3.14}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'alias': 3.14})

    # dicts with complex validation
    >>> assert validate({'name': lambda x: x in ['john', 'jane']}, {'name': 'jane'}) == {'name': 'jane'}
    >>> with pytest.raises(AssertionError):
    ...     validate({'name': lambda x: x in ['john', 'jane']}, {'name': 'rose'})

    # dicts with optional k's provide a value for a missing key and validate provided keys
    >>> schema = {'name': lambda x: x == ':optional' and 'jane' or isinstance(x, str)}
    >>> assert validate(schema, {}) == {'name': 'jane'}
    >>> assert validate(schema, {'name': 'rose'}) == {'name': 'rose'}
    >>> with pytest.raises(AssertionError):
    ...     validate(schema, {'name': 123})

    # dicts with only type keys can be empty
    >>> schema = {str: str}
    >>> assert validate(schema, {}) == {}

    # validate is recursive, so nest schemas freely
    >>> schema = {'users': [{'name': (str, str), 'id': int}]}
    >>> obj = {'users': ({'name': ('jane', 'smith'), 'id': 85},
    ...                  {'name': ('john', 'smith'), 'id': 93})}
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
    with s.exceptions.update(lambda x: _prettify(x + _helpful_message(schema, value)), AssertionError):
        if isinstance(schema, dict):
            assert isinstance(value, dict), 'value {} <{}> should be a dict for schema: {} <{}>'.format(value, type(value), schema, type(schema))
            for k in value.keys():
                assert isinstance(k, s.data.string_types), 'thanks to json, dict keys must be str: {}, {}'.format(k, value)
            value, validated_schema_items = _check_for_items_in_value_that_dont_satisfy_schema(schema, value)
            value = _check_for_items_in_schema_missing_in_value(schema, value, validated_schema_items)
        else:
            return _check(schema, value)
        return value


def _check_for_items_in_value_that_dont_satisfy_schema(schema, value):
    validated_schema_items = []
    val = {}
    for k, v in value.items():
        value_mismatch = k not in schema
        type_mismatch = type(k) not in [x for x in schema if isinstance(x, type)] and object not in schema
        assert not value_mismatch or not type_mismatch, '{} <{}> does not match schema keys: {}'.format(k, type(k), ', '.join(['{} <{}>'.format(x, type(x)) for x in schema.keys()]))
        key = type(k) if value_mismatch else k
        validator = schema.get(key, schema.get(object))
        validated_schema_items.append((key, validator))
        with s.exceptions.update(lambda x: x + "\n--key--\n'{}'".format(k), AssertionError):
            val[k] = _check(validator, v)
    return val, validated_schema_items


def _check_for_items_in_schema_missing_in_value(schema, value, validated_schema_items):
    if value or not {type(x) for x in schema.keys()} == {type}: # if schema keys are all types, and value is empty, return
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
                    val = v(':optional')
                    assert val != ':optional', 'you accidentally returned :optional instead of your actual default value for: {}, {}'.format(k, v)
                    value = s.dicts.merge(value, {k: val})
    return value


def _starts_with_keyword(x):
    if x and isinstance(x[0], s.data.string_types) and x[0].startswith(':'):
        return True
    else:
        return False


def _check(validator, value):
    assert not isinstance(validator, set), 'a set cannot be a validator: {}'.format(validator)
    if validator is object:
        return value
    elif isinstance(validator, (list, tuple)):
        assert isinstance(value, (list, tuple)) or _starts_with_keyword(validator), '{} <{}> is not a a seq: {} <{}>'.format(value, type(value), validator, type(validator))
        if isinstance(validator, list):
            if not validator:
                assert not value, 'you schema is an empty sequence, but this is not empty: {}'.format(value)
            elif value:
                assert len(validator) == 1, 'list validators represent variable length iterables and must contain a single validator: {}'.format(validator)
                return s.data.freeze([_check(validator[0], v) for v in value])
            return value
        elif isinstance(validator, tuple):
            if validator and validator[0] == ':or':
                for v in validator[1:]:
                    with s.exceptions.ignore(AssertionError):
                        return _check(v, value)
                raise AssertionError('{} <{}> did not match any of [{}]'.format(value, type(value), ', '.join(['{} <{}>'.format(x, type(x)) for x in validator[1:]])))
            else:
                assert len(validator) == len(value), '{} <{}> mismatched length of validator {} <{}>'.format(value, type(value), validator, type(validator))
                return s.data.freeze([_check(_validator, _val) for _validator, _val in zip(validator, value)])
    elif isinstance(validator, dict):
        assert isinstance(value, dict), '{} <{}> does not match schema {} <{}>'.format(value, type(value), validator, type(validator))
        return validate(validator, value)
    elif isinstance(validator, type):
        val_type = type(value)
        if type(value) in s.data.string_types:
            val_type = str
        assert val_type is validator, '{} <{}> is not a <{}>'.format(value, type(value), validator)
        return value
    elif isinstance(validator, types.FunctionType):
        assert validator(value), '{} <{}> failed validator {}'.format(value, type(value), s.func.source(validator))
        return value
    elif isinstance(validator, s.data.json_types):
        with s.exceptions.ignore(AttributeError):
            value = value.decode('utf-8')
        assert value == validator, '{} <{}> != {} <{}>'.format(value, type(value), validator, type(validator))
        return value
    else:
        raise AssertionError('bad validator {} <{}>'.format(validator, type(validator)))


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

    return '\n\n--obj--\n{}\n--schema--\n{}\n--end--\n'.format(
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


def check(*args, **kwargs):
    def decorator(fn):
        arg_schemas, kwarg_schemas = get_schemas(args, kwargs, fn)
        returns_schema = kwarg_schemas.pop('returns', lambda x: x)
        name = s.func.name(fn)
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            with s.exceptions.update(lambda x: x + '\n--info--\nschema.check failed for {}\n--end--\n'.format(name)):
                assert len(arg_schemas) == len(args), 'you asked to check {} for {} pos args, but {} were provided: {}'.format(name, len(arg_schemas), len(args), args)
                for key, value in kwargs.items():
                    assert key in kwarg_schemas, 'cannot check {} for unknown key: {}={}'.format(name, key, value)
                try:
                    _args = []
                    for i, (schema, arg) in enumerate(zip(arg_schemas, args)):
                        with s.exceptions.update(lambda x: x + '--arg num--\n{}\n--end--\n'.format(i)):
                            _args.append(validate(schema, arg))
                    checker = lambda k, v: validate(kwarg_schemas.get(k, lambda x: x), v)
                    _kwargs = {}
                    for k, v in kwargs.items():
                        with s.exceptions.update(lambda x: x + '--arg keyword--\n{}\n--end--\n'.format(k)):
                            _kwargs[k] = checker(k, v)
                    value = fn(*_args, **_kwargs)
                    if s.trace._is_futury(value):
                        @s.async.coroutine
                        def validator():
                            val = yield value
                            with s.exceptions.update(lambda x: x + '--return value--\n', AssertionError):
                                assert val is not None, 'you cannot return None from s.schema.check\'d function'
                                raise s.async.Return(s.schema.validate(returns_schema, val))
                        return validator()
                    else:
                        assert value is not None, 'you cannot return None from s.schema.check\'d function'
                        with s.exceptions.update(lambda x: x + '--return value--\n'):
                            return s.schema.validate(returns_schema, value)
                except AssertionError as e:
                    s.exceptions.update(e, lambda x: x + '\n\n--function--\n{}\n--end--\n'.format(name))
                    raise
        return decorated
    return decorator
