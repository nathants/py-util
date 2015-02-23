from __future__ import print_function, absolute_import
import sys
import traceback
import six
import functools
import re
import pprint
import s
import types
import inspect
import concurrent.futures


_schema_commands = (':or',
                    ':fn',
                    ':optional',
                    ':maybe')


def is_valid(schema, value, freeze=True):
    try:
        validate(schema, value, freeze=freeze)
        return True
    except AssertionError:
        return False


# TODO how to schema this set of objects: (':foo', 1, 2), (':foo', 3, 4, 5)
# different lengths? *args?
# think about schemaing the args to s.func.pipe()


def validate(schema, value, freeze=True):
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
    try:
        with s.exceptions.update(_updater(schema, value), AssertionError):
            # TODO does this block belong in _check()? should they even be seperate?
            if isinstance(value, (s.async.Future, concurrent.futures.Future)):
                future = type(value)()
                @value.add_done_callback
                def fn(f):
                    try:
                        future.set_result(validate(schema, f.result()))
                    except Exception as e:
                        future.set_exception(e)
                return future
            elif isinstance(schema, dict):
                assert isinstance(value, dict), 'value {} <{}> should be a dict for schema: {} <{}>'.format(value, type(value), schema, type(schema))
                value, validated_schema_items = _check_for_items_in_value_that_dont_satisfy_schema(schema, value)
                value = _check_for_items_in_schema_missing_in_value(schema, value, validated_schema_items)
            else:
                value = _check(schema, value)
            if freeze:
                if type(schema) is type:
                    with s.exceptions.ignore(ValueError):
                        value = s.data.freeze(value)
                else:
                    value = s.data.freeze(value)
            return value
    except AssertionError as e:
        raise SchemaError(*e.args)


def _formdent(x):
    return s.strings.indent(pprint.pformat(x, width=1), 2)


def _update_functions(schema):
    def fn(x):
        if isinstance(x, types.FunctionType):
            if six.PY3:
                filename, linenum = x.__code__.co_filename, x.__code__.co_firstlineno
            else:
                filename, linenum = x.func_code.co_filename, x.func_code.co_firstlineno
            x = 'lambda:{filename}:{linenum}'.format(**locals())
        return x
    return s.seqs.walk(fn, schema)


def _updater(schema, value):
    schema = _update_functions(schema)
    return lambda x: _prettify(x + '\nobj:\n{}\nschema:\n{}'.format(_formdent(value), _formdent(schema)))


class SchemaError(AssertionError):
    pass


def _check_for_items_in_value_that_dont_satisfy_schema(schema, value):
    validated_schema_items = []
    val = {}
    for k, v in value.items():
        value_match = k in schema
        type_match = type(k) in [x for x in schema if isinstance(x, type)] or object in schema
        assert value_match or type_match, '{} <{}> does not match schema keys: {}'.format(k, type(k), ', '.join(['{} <{}>'.format(x, type(x)) for x in schema.keys()]))
        key = k if value_match else type(k)
        validator = schema.get(key) or schema[object]
        validated_schema_items.append((key, validator))
        with s.exceptions.update("key:\n  {}".format(k), AssertionError):
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
        assert isinstance(value, (list, tuple)) or _starts_with_keyword(validator), '{} <{}> is not a seq: {} <{}>'.format(value, type(value), validator, type(validator))
        if validator and validator[0] in _schema_commands:
            if validator[0] == ':optional':
                assert len(validator) == 3, ':optional schema should be (:optional, schema, default-value), not: {}'.format(validator)
                return _check(validator[1], value)
            elif validator[0] == ':maybe':
                assert len(validator) == 2, ':maybe schema should be (:maybe, schema), not: {}'.format(validator)
                if value is None:
                    return None
                return _check(validator[1], value)
            elif validator[0] == ':or':
                for v in validator[1:]:
                    tracebacks = []
                    try:
                        return _check(v, value)
                    except AssertionError as e:
                        tracebacks.append(traceback.format_exc())
                raise AssertionError('{} <{}> did not match any of [{}]\n{}'.format(value, type(value), ', '.join(['{} <{}>'.format(x, type(x)) for x in validator[1:]]), '\n'.join(tracebacks)))
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
        valid_str = isinstance(value, s.data.string_types) and validator in s.data.string_types
        assert valid_str or isinstance(value, validator), '{} <{}> is not a <{}>'.format(value, type(value), validator)
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


def _prettify(x):
    return re.sub("\<\w+ \'([\w\.]+)\'\>", r'\1', str(x))


def get_schemas(fn, args, kwargs):
    arg_schemas, kwarg_schemas = _read_annotations(fn, args, kwargs)
    schemas = {'yield': kwarg_schemas.pop('_yield', object),
               'send': kwarg_schemas.pop('_send', object),
               'return': kwarg_schemas.pop('_return', object),
               'args': kwarg_schemas.pop('_args', None),
               'kwargs': kwarg_schemas.pop('_kwargs', None)}
    schemas['arg'], schemas['kwarg'] = arg_schemas, kwarg_schemas
    return schemas


def _read_annotations(fn, arg_schemas, kwarg_schemas):
    if not arg_schemas and six.PY3:
        sig = inspect.signature(fn)
        arg_schemas = [x.annotation
                       for x in sig.parameters.values()
                       if x.default is inspect._empty
                       and x.annotation is not inspect._empty
                       and x.kind is x.POSITIONAL_OR_KEYWORD]
        val = {x.name: x.annotation
               for x in sig.parameters.values()
               if x.default is not inspect._empty
               or x.kind is x.KEYWORD_ONLY
               and x.annotation is not inspect._empty}
        val = s.dicts.merge(val,
                            {'_args': x.annotation
                             for x in sig.parameters.values()
                             if x.annotation is not inspect._empty
                             and x.kind is x.VAR_POSITIONAL},
                            freeze=False)
        val = s.dicts.merge(val,
                            {'_kwargs': x.annotation
                             for x in sig.parameters.values()
                             if x.annotation is not inspect._empty
                             and x.kind is x.VAR_KEYWORD},
                            freeze=False)
        kwarg_schemas = s.dicts.merge(kwarg_schemas, val, freeze=False)
        if sig.return_annotation is not inspect._empty:
            kwarg_schemas['_return'] = sig.return_annotation
    assert arg_schemas or kwarg_schemas, 'you asked to check, but provided no schemas for: {}'.format(s.func.name(fn))
    return arg_schemas, kwarg_schemas


def _check_args(args, kwargs, name, freeze, schemas):
    # TODO better to use inspect.getcallargs() for this? would change the semantics of pos arg checking. hmmn...
    assert len(schemas['arg']) == len(args) or schemas['args'], 'you asked to check {} for {} pos args, but {} were provided: {}\n{}'.format(name, len(schemas['arg']), len(args), args, schemas)
    _args = []
    for i, (schema, arg) in enumerate(zip(schemas['arg'], args)):
        with s.exceptions.update('pos arg num:\n  {}'.format(i), AssertionError):
            _args.append(validate(schema, arg, freeze=freeze))
    if schemas['args'] and args[len(schemas['arg']):]:
        _args += validate(schemas['args'], args[len(schemas['arg']):], freeze=freeze)
    _kwargs = {}
    for k, v in kwargs.items():
        if k in schemas['kwarg']:
            with s.exceptions.update('keyword arg:\n  {}'.format(k), AssertionError):
                _kwargs[k] = validate(schemas['kwarg'][k], v, freeze=freeze)
        elif schemas['kwargs']:
            with s.exceptions.update('keyword args schema failed.', AssertionError):
                _kwargs[k] = validate(schemas['kwargs'], {k: v}, freeze=freeze)[k]
        else:
            raise AssertionError('cannot check {} for unknown key: {}={}'.format(name, k, v))
    return _args, _kwargs


def _fn_check(decoratee, name, freeze, schemas):
    @functools.wraps(decoratee)
    def decorated(*args, **kwargs):
        with s.exceptions.update('schema.check failed for function:\n  {}'.format(name), AssertionError, when=lambda x: 'failed for ' not in x):
            # TODO dry this out with _gen_check()
            if args and inspect.ismethod(getattr(args[0], decoratee.__name__, None)):
                a, kwargs = _check_args(args[1:], kwargs, name, freeze, schemas)
                args = [args[0]] + a
            else:
                args, kwargs = _check_args(args, kwargs, name, freeze, schemas)
            value = decoratee(*args, **kwargs)
            with s.exceptions.update('schema.check failed for return value of function:\n {}'.format(name), AssertionError):
                output = validate(schemas['return'], value, freeze=freeze)
            return output
    return decorated


def _gen_check(decoratee, name, freeze, schemas):
    @functools.wraps(decoratee)
    def decorated(*args, **kwargs):
        with s.exceptions.update('schema.check failed for generator:\n  {}'.format(name), AssertionError, when=lambda x: 'failed for ' not in x):
            if args and inspect.ismethod(getattr(args[0], decoratee.__name__, None)):
                a, kwargs = _check_args(args[1:], kwargs, name, freeze, schemas)
                args = [args[0]] + a
            else:
                args, kwargs = _check_args(args, kwargs, name, freeze, schemas)
            generator = decoratee(*args, **kwargs)
            to_send = None
            first_send = True
            send_exception = False
            while True:
                if not first_send:
                    with s.exceptions.update('schema.check failed for send value of generator:\n {}'.format(name), AssertionError):
                        to_send = validate(schemas['send'], to_send)
                first_send = False
                try:
                    if send_exception:
                        to_yield = generator.throw(*send_exception)
                        send_exception = False
                    else:
                        to_yield = generator.send(to_send)
                    with s.exceptions.update('schema.check failed for yield value of generator:\n {}'.format(name), AssertionError):
                        to_yield = validate(schemas['yield'], to_yield)
                except (s.async.Return, StopIteration) as e:
                    with s.exceptions.update('schema.check failed for return value of generator:\n {}'.format(name), AssertionError):
                        e.value = validate(schemas['return'], getattr(e, 'value', None))
                    raise
                try:
                    to_send = yield to_yield
                except:
                    send_exception = sys.exc_info()
    return decorated


@s.hacks.optionally_parameterized_decorator
def check(*args, **kwargs):
    # TODO add doctest with :fn and args/kwargs
    def decorator(decoratee):
        freeze = kwargs.pop('_freeze', True)
        name = s.func.name(decoratee)
        schemas = get_schemas(decoratee, args, kwargs)
        if inspect.isgeneratorfunction(decoratee):
            decorated = _gen_check(decoratee, name, freeze, schemas)
        else:
            decorated = _fn_check(decoratee, name, freeze, schemas)
        decorated._schema = schemas['arg'], {k: v for k, v in list(schemas['kwarg'].items()) + [['_return', schemas['return']]]}
        return decorated
    return decorator
