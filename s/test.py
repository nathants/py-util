from __future__ import absolute_import, print_function
import sys
import time
import itertools
import types
import traceback
import collections
import os
import s
import itertools as i


_max_seconds = .0075


@s.fn.logic
def _test_file(code_file):
    assert not code_file.startswith('/')
    assert code_file.endswith('.py')
    val = code_file.split('/')
    val[0] = 'test_{}'.format(val[0])
    val = val[:1] + ['fast'] + val[1:]
    val = '/'.join(val)
    return val


@s.fn.logic
def _code_file(test_file):
    assert not test_file.startswith('/')
    assert test_file.endswith('.py')
    val = test_file.split('/')
    val[0] = val[0].replace('test_', '')
    val.pop(1)
    val = '/'.join(val)
    return val


@s.fn.logic
def _git_root(climb_data):
    climb_data = list(climb_data)
    val = [path for path, dirs, _ in climb_data if '.git' in dirs]
    assert val, 'didnt find git root from: {}'.format(climb_data[0][0])
    return val[0]


@s.fn.logic
def _filter_test_files(walk_data):
    return [os.path.join(path, f)
            for path, _, files in walk_data
            for f in files
            if f.endswith('.py')
            and not f.startswith('.')
            and '_flymake' not in f
            and '/build/' not in path
            and len(path.split('/')) >= 2
            and path.split('/')[-2].startswith('test_')]


@s.fn.logic
def _filter_fast_test_files(paths):
    return [x for x in paths if 'fast' in x.split('/')]


@s.fn.logic
def _filter_slow_test_files(paths):
    return [x for x in paths if 'slow' in x.split('/')]


@s.fn.logic
def _filter_code_files(walk_datas):
    return [os.path.join(path, f)
            for data in walk_datas
            for path, _, files in data
            for f in files
            if f.endswith('.py')
            and not f.startswith('.')
            and '_flymake' not in f
            and '/build/' not in path
            and not any(x.startswith('test_') for x in path.split('/'))]


@s.fn.logic
def _python_packages(walk_data):
    walk_data = list(walk_data)
    return [path
            for path, _, files in walk_data
            if os.path.basename(path) in walk_data[0][1]
            and '__init__.py' in files]


@s.fn.glue
def _mapwalk(dirs):
    return [s.shell.walk(x) for x in dirs]


@s.fn.glue
def _collect_tests(test_file):
    keep = ['<Function']
    text = s.shell.run('py.test --collect-only', test_file)
    return [x.strip() for x in text.splitlines()
            if any(x.strip().startswith(y) for y in keep)]


def _result(result, path, seconds):
    pred = lambda x: not x.startswith('test_')
    path = itertools.dropwhile(pred, path.split('/'))
    path = '.'.join(path)
    return collections.namedtuple('result', 'result path seconds')(result, path, seconds)


@s.fn.glue
def _run_test(path, name, test):
    _bak = s.fn._state.get('_stack')
    s.fn._state['_stack'] = None # mock out _stack, since its used *here* as well
    with s.time.timer() as t:
        try:
            test()
            val = False
        except:
            tb = traceback.format_exc()
            try:
                val = _pytest_insight(path, name)
            except:
                val = tb + '\nFAILED to reproduce test failure in py.test, go investigate!'
    if not val and t['seconds'] > _max_seconds:
        val = ' {} took {} seconds, slower than max seconds {}'.format(name, t['seconds'], _max_seconds)
    s.fn._state['_stack'] = _bak
    return _result(val, '{}:{}()'.format(path, name), round(t['seconds'], 3))


@s.fn.flow
def _test(path):
    assert path.endswith('.py')
    name = s.shell.module_name(path)
    try:
        module = __import__(name, fromlist='*')
    except:
        return [_result(traceback.format_exc(), path, 0)]
    items = module.__dict__.items()
    items = [(k, v) for k, v in items
             if k not in ['__builtins__', '__builtin__']
             and k.startswith('test')
             and isinstance(v, types.FunctionType)]
    path = module.__file__.replace('.pyc', '.py')
    # todo should i run setups/teardowns? or enforce pure testing?
    return [_run_test(path, k, v) for k, v in items] or [_result(None, path, 0)]


@s.fn.flow
def _pytest_insight(test_file, query):
    val = s.shell.run('py.test -qq -k', query, test_file, warn=True)
    assert not any(x.startswith('ERROR: file not found:') for x in val.output.splitlines())
    assert not any(x.startswith('ERROR: not found:') for x in val.output.splitlines())
    assert os.path.isfile(test_file)
    assert val.exitcode != 0
    return s.fn.thrush(
        val.output,
        str.splitlines,
        reversed,
        lambda x: i.dropwhile(lambda y: y.startswith('===='), x),
        lambda x: i.takewhile(lambda y: not y.startswith('_____'), x),
        list,
        reversed,
        list,
        lambda x: ['-' * 80] + x + ['-' * 80],
        '\n'.join,
    )


@s.fn.logic
def _linenum(text):
    return [int(x.split(', line ')[-1].split(',')[0])
            for x in text.splitlines()
            if 'File "<string>"' in x][-1]


@s.fn.flow
def _test_all(paths):
    return [_test(x) for x in paths]


@s.fn.flow
def all_test_files():
    return s.fn.thrush(
        s.shell.climb(),
        _git_root,
        s.shell.walk,
        _filter_test_files
    )


@s.fn.flow
def all_slow_test_files():
    return s.fn.thrush(
        all_test_files(),
        _filter_slow_test_files,
    )


@s.fn.flow
def all_fast_test_files():
    return s.fn.thrush(
        all_test_files(),
        _filter_fast_test_files,
    )


@s.fn.flow
def all_code_files():
    return s.fn.thrush(
        s.shell.climb(),
        _git_root,
        s.shell.walk,
        _python_packages,
        _mapwalk,
        _filter_code_files,
    )


@s.fn.flow
def run_tests_once():
    return s.fn.thrush(
        all_fast_test_files(),
        _test_all,
    )


@s.fn.flow
def run_tests_auto():
    with s.shell.climb_git_root():
        dirs = _python_packages(s.shell.walk())
        predicate = lambda f: (f.endswith('.py')
                               and not f.startswith('.')
                               and '_flymake' not in f)
        val = s.shell.walk_files_mtime(dirs, predicate)
        modules = [s.shell.module_name(x) for x, _ in val]
        last = None
        while True:
            now = s.shell.walk_files_mtime(dirs, predicate)
            if last != now:
                [sys.modules.pop(x, None) for x in modules]
                yield run_tests_once()
            time.sleep(.01)
            last = now
