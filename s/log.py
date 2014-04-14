import os
import sys
import pprint
import logging
import s


_standard_format = '[%(levelname)s] [%(asctime)s] [%(name)s] [%(pathname)s] %(message)s'


_short_format = '[%(levelname)s] %(message)s'


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


def _add_handler(handler, level, format, pprint):
    handler.setLevel(level.upper())
    handler.setFormatter(Formatter(format, pprint))
    logging.root.addHandler(handler)


def _get_format(format, short):
    return (format if format
            else _short_format if short
            else _standard_format)


@s.cached.func
def setup(level='info', short=False, pprint=False, format=None):
    level = _get_level(level)
    short = _get_short(short)
    format = _get_format(format, short)
    map(logging.root.removeHandler, logging.root.handlers)
    _add_handler(logging.StreamHandler(sys.stderr), level, format, pprint)
    logging.root.setLevel(level.upper())


try:
    _pretty_main_skip_types = basestring,
    _pretty_arg_skip_types = basestring, int, long, float
except NameError:
    _pretty_main_skip_types = str, bytes
    _pretty_arg_skip_types = str, bytes, int, float



def _pprint(record):
    if not record._pprint:
        return record
    val = []
    for x in record.args:
        try:
            assert not isinstance(x, _pretty_arg_skip_types)
            val.append(pprint.pformat(x, indent=2, width=10))
        except:
            val.append(x)
    record.args = val
    if not isinstance(record.msg, _pretty_main_skip_types):
        with s.exceptions.ignore():
            record.msg = pprint.pformat(record.msg, indent=2, width=10)
            if not record.args:
                record.msg = '\n' + record.msg
    return record


def _old_style(record):
    with s.exceptions.ignore():
        record.msg = record.msg % record.args
    return record


def _space_join_args(record):
    with s.exceptions.ignore():
        record.msg = ' '.join([str(record.msg)] + map(str, record.args))
        record.args = []
    return record


def _ensure_args_list(record):
    if not isinstance(record.args, (list, tuple)):
        record.args = [record.args]
    return record


def _better_pathname(record):
    if ':' not in record.pathname:
        record.pathname = '/'.join(record.pathname.split('/')[-2:])
        record.pathname = '{}:{}'.format(record.pathname.replace('.py', ''), record.lineno)
    return record


class Formatter(logging.Formatter):
    def __init__(self, fmt, pprint=False):
        self.pprint = pprint
        logging.Formatter.__init__(self, fmt=fmt)

    def format(self, record):
        record._pprint = self.pprint
        record = s.fn.thread(
            record,
            _ensure_args_list,
            _pprint,
            _old_style,
            _space_join_args,
            _better_pathname,
        )
        record.levelname = record.levelname.lower()[0]
        return logging.Formatter.format(self, record)
