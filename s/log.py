from __future__ import absolute_import, print_function
import os
import sys
import pprint
import logging
import logging.handlers
import s
import time

_standard_format = '[%(levelname)s] [%(asctime)s] [%(name)s] [%(pathname)s] %(message)s'


_short_format = '[%(levelname)s] %(message)s'


for _name in ['debug', 'info', 'warn', 'warning', 'error', 'exception']:
    locals()[_name] = getattr(logging, _name)


def _flag_override(var, flag, new_value):
    def fn(val):
        if var in os.environ or flag in sys.argv:
            if flag in sys.argv:
                sys.argv.remove(flag)
            os.environ[var] = ''
            val = new_value
        return val
    return fn


_get_level = _flag_override('_logging_force_debug', '--debug', 'debug')


_get_short = _flag_override('_logging_force_short', '--short', True)


def _make_handler(handler, format, pprint, filter=None):
    handler.setLevel('DEBUG')
    if filter:
        handler.addFilter(filter())
    handler.setFormatter(_Formatter(format, pprint))
    return handler


def _get_format(format, short):
    return (format if format
            else _short_format if short
            else _standard_format)


@s.cached.func
def setup(name=None, level='info', short=False, pprint=False, format=None):
    level = _get_level(level)
    assert level in ('debug', 'info')
    short = _get_short(short)
    format = _get_format(format, short)
    handlers = []

    # if debug not in streaming log, add the debug-only file output handler
    if level == 'info':
        path = _get_debug_path(name)
        s.shell.cron_rm_path_later(path, hours=24)
        handler = logging.handlers.WatchedFileHandler(path)
        handlers.append(_make_handler(handler, format, False, _DebugOnly))

    # add the debug or info level stream handler
    handler = logging.StreamHandler()
    if level != 'debug':
        handlers.append(_make_handler(handler, format, pprint, _NotDebug))
    else:
        handlers.append(_make_handler(handler, format, True))

    # rm all root handlers
    [logging.root.removeHandler(x) for x in logging.root.handlers]
    [logging.root.addHandler(x) for x in handlers]
    logging.root.setLevel('DEBUG')

    # todo how to make logging config immutable? no one should be able to manipulate logging after this call


def _get_debug_path(name):
    caller = s.hacks.get_caller(4)
    funcname = caller.funcname if caller.funcname != '<module>' else '__main__'
    name = s.shell.module_name(caller.filename)
    return '/tmp/{}:{}:{}:debug.log'.format(name, funcname, time.time())


try:
    _pretty_main_skip_types = basestring,
    _pretty_arg_skip_types = basestring, int, long, float
except NameError:
    _pretty_main_skip_types = str, bytes
    _pretty_arg_skip_types = str, bytes, int, float



def _pprint(record):
    indent = 1
    width = 80
    with s.exceptions.ignore():
        pprint_arg = '!pprint' in record.args
        if pprint_arg:
            record.args = tuple(x for x in record.args if x != '!pprint')
        if not record._pprint and not pprint_arg:
            return record
        val = []
        for x in record.args:
            try:
                assert not isinstance(x, _pretty_arg_skip_types)
                x = s.hacks.pformat_prep(x)
                val.append('\n' + pprint.pformat(x, indent=indent, width=width))
            except:
                val.append(x)
        record.args = val
        if not isinstance(record.msg, _pretty_main_skip_types):
            with s.exceptions.ignore():
                record.msg = s.hacks.pformat_prep(record.msg)
                record.msg = pprint.pformat(record.msg, indent=indent, width=width)
                if not record.args:
                    record.msg = '\n' + record.msg
    return record


def _old_style(record):
    with s.exceptions.ignore():
        msg = record.msg % tuple(record.args)
        if msg != record.msg:
            record.args = []
            record.msg = msg

    return record


def _color(record):
    with s.exceptions.ignore():
        record.msg = s.strings.color(record.msg)
    return record


def _space_join_args(record):
    with s.exceptions.ignore():
        record.msg = ' '.join([str(record.msg)] + map(str, record.args))
        record.args = []
    return record


def _ensure_args_list(record):
    with s.exceptions.ignore():
        if not isinstance(record.args, (list, tuple)):
            record.args = [record.args]
    return record


def _better_pathname(record):
    with s.exceptions.ignore():
        if ':' not in record.pathname:
            record.pathname = '/'.join(record.pathname.split('/')[-2:])
            record.pathname = '{}:{}'.format(record.pathname, record.lineno)
    return record


def _short_levelname(record):
    with s.exceptions.ignore():
        record.levelname = record.levelname.lower()[0]
    return record


class _DebugOnly(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.DEBUG


class _NotDebug(logging.Filter):
    def filter(self, record):
        return record.levelno != logging.DEBUG


def _process_record(record):
    if not hasattr(record, '_processed'):
        record = s.fn.thrush(
            record,
            _ensure_args_list,
            _pprint,
            _old_style,
            _space_join_args,
            _better_pathname,
            _color,
            _short_levelname,
        )
        record._processed = True
    return record


class _Formatter(logging.Formatter):
    def __init__(self, fmt, pprint=False):
        self.pprint = pprint
        logging.Formatter.__init__(self, fmt=fmt)

    def format(self, record):
        record._pprint = self.pprint
        return logging.Formatter.format(self, _process_record(record))
