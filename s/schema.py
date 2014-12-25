from __future__ import print_function, absolute_import
import six
import functools
import re
import pprint
import s
import types
import inspect


_schema_commands = (':or',
                    ':fn',
                    ':optional')


def is_valid(schema, value):
    try:
        validate(schema, value)
        return True
    except AssertionError:
        return False


def validate(schema, value, _freeze=True):
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

    # dicts with :optional k's provide a value for a missing key and validate provided keys
    >>> schema = {'name': (':optional', str, 'jane')}
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
            value = _check(schema, value)
        if _freeze:
            if type(schema) is type:
                with s.exceptions.ignore(ValueError):
                    value = s.data.freeze(value)
            else:
                value = s.data.freeze(value)
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
                if isinstance(k, type): # if a type key is missing, look for an item that satisfies it
                    for vk, vv in value.items():
                        with s.exceptions.ignore(AssertionError):
                            validate(k, vk)
                            validate(v, vv)
                            break
                    else:
                        raise AssertionError('{} <{}> is missing (key, value) pair: {} <{}>, {} <{}>'.format(value, type(value), k, type(k), v, type(v)))
                elif isinstance(v, (list, tuple)) and v and v[0] == ':optional':
                    assert len(v) == 3, ':optional schema should be (:optional, schema, default-value), not: {}'.format(v)
                    _, schema, default_value = v
                    value = s.dicts.merge(value, {k: validate(schema, default_value)}, freeze=False)
                else:
                    raise AssertionError('{} <{}> is missing required key: {} <{}>'.format(value, type(value), k, type(k)))
    return value


def _starts_with_keyword(x):
    if x and isinstance(x[0], s.data.string_types) and x[0].startswith(':'):
        return True
    else:
        return False


def _check(validator, value):
    # TODO break this up into well named pieces
    assert not isinstance(validator, set), 'a set cannot be a validator: {}'.format(validator)
    if validator is object:
        return value
    elif isinstance(validator, (list, tuple)):
        assert isinstance(value, (list, tuple)) or _starts_with_keyword(validator), '{} <{}> is not a a seq: {} <{}>'.format(value, type(value), validator, type(validator))
        if validator and isinstance(validator[0], s.data.string_types) and validator[0] in _schema_commands:
            if validator[0] == ':optional':
                assert len(validator) == 3, ':optional schema should be (:optional, schema, default-value), not: {}'.format(validator)
                return _check(validator[1], value)
            elif validator[0] == ':or':
                for v in validator[1:]:
                    with s.exceptions.ignore(AssertionError):
                        return _check(v, value)
                raise AssertionError('{} <{}> did not match any of [{}]'.format(value, type(value), ', '.join(['{} <{}>'.format(x, type(x)) for x in validator[1:]])))
            elif validator[0] == ':fn':
                assert isinstance(value, types.FunctionType), '{} <{}> is not a function'.format(value, type(value))
                assert len(validator) in [2, 3], ':fn schema should be (:fn, [<args>...], {<kwargs>: <val>, ...}) or (:fn, [<args>...]), not: {}'.format(validator)
                try:
                    args, kwargs = validator[1:]
                except ValueError:
                    [args], kwargs = validator[1:], {}
                try:
                    _args, _kwargs = value._schema
                except ValueError:
                    [_args], _kwargs = value._schema, {}
                assert _args == args, 'pos args {_args} did not match {args}'.format(**locals())
                assert _kwargs == kwargs, 'kwargs {_kwargs} did not match {kwargs}'.format(**locals())
                return value
        elif isinstance(validator, list):
            if not validator:
                assert not value, 'you schema is an empty sequence, but this is not empty: {}'.format(value)
            elif value:
                assert len(validator) == 1, 'list validators represent variable length iterables and must contain a single validator: {}'.format(validator)
            return [_check(validator[0], v) for v in value]
        elif isinstance(validator, tuple):
            assert len(validator) == len(value), '{} <{}> mismatched length of validator {} <{}>'.format(value, type(value), validator, type(validator))
            return [_check(_validator, _val) for _validator, _val in zip(validator, value)]
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
    if not arg_schemas and six.PY3:
        sig = inspect.signature(fn)
        arg_schemas = [x.annotation
                       for x in sig.parameters.values()
                       if x.default is inspect._empty
                       and x.annotation is not inspect._empty]
        val = {x.name: x.annotation
               for x in sig.parameters.values()
               if x.default is not inspect._empty
               and x.annotation is not inspect._empty}
        kwarg_schemas = s.dicts.merge(kwarg_schemas, val, freeze=False)
        if sig.return_annotation is not inspect._empty:
            kwarg_schemas['_return'] = sig.return_annotation
    assert arg_schemas or kwarg_schemas, 'you asked to check, but provided no schemas for: {}'.format(s.func.name(fn))
    return arg_schemas, kwarg_schemas


def _check_args(args, kwargs, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze):
    assert len(arg_schemas) == len(args) or args_schema, 'you asked to check {} for {} pos args, but {} were provided: {}'.format(name, len(arg_schemas), len(args), args)
    _args = []
    for i, (schema, arg) in enumerate(zip(arg_schemas, args)):
        with s.exceptions.update(lambda x: x + '\n--arg num--\n{}\n--end--\n'.format(i)):
            _args.append(validate(schema, arg, _freeze=_freeze))
    if args_schema and args[len(arg_schemas):]:
        _args += validate(args_schema, args[len(arg_schemas):], _freeze=_freeze)
    _kwargs = {}
    for k, v in kwargs.items():
        if k in kwarg_schemas:
            with s.exceptions.update(lambda x: x + '\n--arg keyword--\n{}\n--end--\n'.format(k)):
                _kwargs[k] = validate(kwarg_schemas[k], v, _freeze=_freeze)
        elif kwargs_schema:
            _kwargs[k] = validate(kwargs_schema, {k: v}, _freeze=_freeze)[k]
        else:
            raise AssertionError('cannot check {} for unknown key: {}={}'.format(name, k, v))
    return _args, _kwargs


def _fn_check(decoratee, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze, returns_schema):
    @functools.wraps(decoratee)
    def decorated(*args, **kwargs):
        with s.exceptions.update(lambda x: x + '\n--info--\nschema.check failed for function: {}\n--end--\n'.format(name)):
            args, kwargs = _check_args(args, kwargs, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze)
            value = decoratee(*args, **kwargs)
            assert value is not None, "you cannot return None from s.schema.check'd function"
            return validate(returns_schema, value, _freeze=_freeze)
    return decorated


# TODO too many args, make this a schema'd dict instead!
def _gen_check(decoratee, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze, returns_schema, sends_schema, yields_schema):
    @functools.wraps(decoratee)
    def decorated(*args, **kwargs):
        args, kwargs = _check_args(args, kwargs, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze)
        generator = decoratee(*args, **kwargs)
        to_send = None
        first_send = True
        while True:
            if not first_send:
                to_send = validate(sends_schema, to_send)
            first_send = False
            try:
                to_yield = generator.send(to_send)
                to_yield = validate(yields_schema, to_yield)
            except (s.async.Return, StopIteration) as e:
                e.value = s.schema.validate(returns_schema, getattr(e, 'value', None))
                assert e.value is not None, "you cannot return None from s.schema.check'd function"
                raise
            to_send = yield to_yield
    return decorated


def check(*args, **kwargs):
    # TODO add doctest with :fn and args/kwargs
    def decorator(decoratee):
        _freeze = kwargs.pop('_freeze', True)
        arg_schemas, kwarg_schemas = get_schemas(args, kwargs, decoratee)

        # TODO args->_args, kwargs->_kwargs
        kwargs_schema = kwarg_schemas.pop('kwargs', None)
        args_schema = kwarg_schemas.pop('args', None)

        returns_schema = kwarg_schemas.pop('_return', object)
        name = s.func.name(decoratee)

        if inspect.isgeneratorfunction(decoratee):
            print("huh?")
            sends_schema = kwarg_schemas.pop('_sends', object)
            yields_schema = kwarg_schemas.pop('_yields', object)
            decorated = _gen_check(decoratee, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze, returns_schema, sends_schema, yields_schema)
        else:
            decorated = _fn_check(decoratee, arg_schemas, kwarg_schemas, args_schema, kwargs_schema, name, _freeze, returns_schema)

        decorated._schema = arg_schemas, {k: v for k, v in list(kwarg_schemas.items()) + [['_return', returns_schema]]}
        return decorated
    return decorator
