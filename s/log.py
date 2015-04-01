from __future__ import absolute_import, print_function
import logging
import logging.handlers
import s.func
import s.cached
import s.strings
import s.exceptions
import s.hacks
import contextlib


_standard_format = '[%(levelname)s] [%(asctime)s] [%(name)s] [%(pathname)s] %(message)s'


_short_format = '[%(levelname)s] %(message)s'


def _get_format(format, short):
    return (format if format
            else _short_format if s.hacks.override('--short') or short
            else _standard_format)


@s.cached.func
def setup(name=None, level='info', short=False, format=None):
    level = ('debug' if s.shell.override('--debug') else level).upper()
    for x in logging.root.handlers:
        logging.root.removeHandler(x)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(_Formatter(_get_format(format, short)))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)


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


def _process_record(record):
    if not hasattr(record, '_processed'):
        record = _better_pathname(record)
        record = _short_levelname(record)
        record._processed = True
    return record


class _Formatter(logging.Formatter):
    def format(self, record):
        record = _process_record(record)
        return logging.Formatter.format(self, record)


@contextlib.contextmanager
def disable(*loggers):
    levels = []
    for name in loggers:
        assert isinstance(name, str), 'loggers must be a list of string names of loggers '
        logger = logging.getLogger(name)
        levels.append(logger.level)
        logger.setLevel('ERROR')
    try:
        yield
    except:
        raise
    finally:
        for level, name in zip(levels, loggers):
            logging.getLogger(name).setLevel(level)
