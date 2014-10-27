from __future__ import absolute_import, print_function
import re
import sys
import time
import types
import traceback
import os
import s
import itertools
import multiprocessing
import Queue


@s.func.flow
def code_file(test_file):
    assert os.path.isfile(test_file), 'no such test_file: {}'.format(test_file)
    test_file_rel_path = s.shell.rel_path(test_file)
    root = test_file.split(test_file_rel_path)[0]
    path = os.path.join(root, _code_file(test_file_rel_path))
    assert os.path.isfile(path), 'no such code_file: {}'.format(path)
    return path


@s.func.flow
def test_file(code_file):
    assert os.path.isfile(code_file), 'no such code_file: {}'.format(code_file)
    code_file_rel_path = s.shell.rel_path(code_file)
    root = code_file.split(code_file_rel_path)[0]
    path = os.path.join(root, _test_file(code_file_rel_path))
    assert os.path.isfile(path), 'no such test_file: {}'.format(path)
    return path


@s.func.logic
def _test_file(code_file):
    assert not code_file.startswith('/'), 'code_file is not relative path from project root: {}'.format(code_file)
    assert code_file.endswith('.py'), 'code_file does not end with .py: {}'.format(code_file)
    val = code_file.split('/')
    val[0] = 'test_{}'.format(val[0])
    val = val[:1] + ['fast'] + val[1:]
    val = '/'.join(val)
    return val


@s.func.logic
def _code_file(test_file):
    assert not test_file.startswith('/'), 'test_file is not relative path from project root: {}'.format(test_file)
    assert test_file.endswith('.py'), 'test_file does not end with .py: {}'.format(test_file)
    val = test_file.split('/')
    val[0] = val[0].replace('test_', '')
    val.pop(1)
    val = '/'.join(val)
    return val


@s.func.logic
def _git_root(climb_data):
    climb_data = list(climb_data)
    val = [path for path, dirs, _ in climb_data if '.git' in dirs]
    assert val, 'didnt find git root from: {}'.format(climb_data[0][0])
    return val[0]


@s.func.logic
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


@s.func.logic
def _filter_fast_test_files(paths):
    return [x for x in paths if 'fast' in x.split('/')]


@s.func.logic
def _filter_slow_test_files(paths):
    return [x for x in paths if 'slow' in x.split('/')]


@s.func.logic
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


@s.func.logic
def _python_packages(walk_data):
    walk_data = list(walk_data)
    return [path
            for path, _, files in walk_data
            if os.path.basename(path) in walk_data[0][1]
            and '__init__.py' in files]


@s.func.glue
def _mapwalk(dirs):
    return [s.shell.walk(x) for x in dirs]


@s.func.glue
def _collect_tests(test_file):
    keep = ['<Function']
    text = s.shell.run('py.test --collect-only', test_file)
    return [x.strip() for x in text.splitlines()
            if any(x.strip().startswith(y) for y in keep)]


def _result(result, path, seconds):
    pred = lambda x: not x.startswith('test_')
    path = itertools.dropwhile(pred, path.split('/'))
    path = '.'.join(path)
    return s.dicts.new(locals(), 'result', 'path', 'seconds')


@s.func.glue
def _run_test(path, name, test):
    _bak = s.func._state.get('_stack')
    s.func._state['_stack'] = None # stub out _stack, since its used *here* as well
    try:
        with s.time.timer() as t:
            try:
                test()
                val = False
            except:
                tb = traceback.format_exc()
                try:
                    val = _pytest_insight(path, name)
                except:
                    val = tb + '\nFAILED to reproduce test failure in py.test, go investigate!' + traceback.format_exc()
        return _result(val, '{}:{}()'.format(path, name), round(t['seconds'], 3))
    finally:
        s.func._state['_stack'] = _bak


@s.func.flow
def _test(test_path):
    assert test_path.endswith('.py'), 'test_path does not end with .py: {}'.format(test_path)
    assert os.path.isfile(test_path), 'no such file: {}'.format(test_path)
    name = s.shell.module_name(test_path)
    try:
        module_name = __import__(name, fromlist='*')
    except:
        return [_result(traceback.format_exc(), test_path, 0)]
    items = module_name.__dict__.items()
    items = [(k, v) for k, v in items
             if k not in ['__builtins__', '__builtin__']
             and k.startswith('test')
             and isinstance(v, types.FunctionType)]
    test_path = module_name.__file__.replace('.pyc', '.py')
    return [_run_test(test_path, k, v) for k, v in items] or [_result(None, test_path, 0)]


def _format_pytest_output(text):
    return s.func.thrush(
        text,
        str.splitlines,
        reversed,
        lambda x: itertools.dropwhile(lambda y: y.startswith('===='), x),
        lambda x: itertools.takewhile(lambda y: not y.startswith('_____'), x),
        lambda x: [y for y in x if '! Interrupted: stopping' not in y],
        list,
        reversed,
        list,
        lambda x: ['-' * 40] + x + ['-' * 40],
        '\n'.join,
    )


@s.func.flow
def _pytest_insight(test_file, query):
    assert os.path.isfile(test_file), 'no such file: {}'.format(test_file)
    val = s.shell.run('py.test -qq -k', query, test_file, warn=True)
    assert not any(x.startswith('ERROR: file not found:') for x in val['output'].splitlines())
    assert not any(x.startswith('ERROR: not found:') for x in val['output'].splitlines())
    assert val['exitcode'] != 0
    return _format_pytest_output(val['output'])


@s.func.logic
def _linenum(text):
    return [int(x.split(', line ')[-1].split(',')[0])
            for x in text.splitlines()
            if 'File "<string>"' in x][-1]


@s.func.flow
def _test_all(paths):
    return [_test(x) for x in paths]


@s.func.flow
def all_test_files():
    return s.func.thrush(
        s.shell.climb(),
        _git_root,
        s.shell.walk,
        _filter_test_files,
        sorted,
    )


@s.func.flow
def slow_test_files():
    return s.func.thrush(
        all_test_files(),
        _filter_slow_test_files,
    )


@s.func.flow
def fast_test_files():
    return s.func.thrush(
        all_test_files(),
        _filter_fast_test_files,
    )


@s.func.flow
def code_files():
    return s.func.thrush(
        s.shell.climb(),
        _git_root,
        s.shell.walk,
        _python_packages,
        _mapwalk,
        _filter_code_files,
        sorted,
    )


@s.func.flow
def run_tests_once():
    return s.func.thrush(
        fast_test_files(),
        _test_all,
    )


def _run_slow_tests():
    inq = multiprocessing.Queue()
    outq = multiprocessing.Queue()
    state = {'output': ''}
    def main():
        test_files = slow_test_files()
        while True:
            inq.get()
            result = s.shell.run('py.test -x --tb native', *test_files, warn=True)
            if result['exitcode'] != 0:
                text = _format_pytest_output(result['output'])
                outq.put(text)
            else:
                outq.put('')
    s.proc.new(main)
    def run():
        with s.exceptions.ignore(Queue.Full):
            inq.put(None, block=False)
    def results():
        with s.exceptions.ignore(Queue.Empty):
            state['output'] = outq.get(block=False)
        return state['output']
    return run, results


@s.func.flow
def run_tests_auto():
    run_slow_tests, slow_tests_results = _run_slow_tests()
    with s.shell.climb_git_root():
        dirs = _python_packages(s.shell.walk())
        predicate = lambda f: (f.endswith('.py')
                               and not f.startswith('.')
                               and '_flymake' not in f)
        orig = s.shell.walk_files_mtime(dirs, predicate)
        # TODO update modules when orig.filepaths != now.filepaths, so that
        # adding a new file doesnt require a restart.
        # module_name() hits disk, so should call it rarely or pay penalty
        modules = [s.shell.module_name(x['filepath']) for x in orig]
        last = None
        slow_tests_output = None
        while True:
            now = s.shell.walk_files_mtime(dirs, predicate)
            if last != now or slow_tests_results() != slow_tests_output:
                slow_tests_output = slow_tests_results()
                run_slow_tests()
                [sys.modules.pop(x, None) for x in modules]
                yield run_tests_once() + [[{'result': slow_tests_output,
                                            'path': 'test_*/slow/*.py',
                                            'seconds': 0}]]
            time.sleep(.01)
            last = now


@s.func.logic
def _parse_coverage(module_name, text):
    regex = re.compile('(?P<name>[\w\/]+) +\d+ +\d+ +(?P<percent>\d+)% +(?P<missing>[\d\-\, ]+)')
    matches = map(regex.search, text.splitlines())
    matches = [x.groupdict() for x in matches if x]
    if not matches:
        return {'percent': '0',
                'missing': [],
                'name': module_name}
    else:
        if len(matches) > 1:
            matches = [x for x in matches if x['name'] == module_name.replace('.', '/') + '/__init__']
        assert len(matches) == 1, 'found multiple matches: {}'.format(matches)
        data = matches.pop()
        return {'name': module_name,
                'percent': data['percent'],
                'missing': (data['missing'].strip().split(', ')
                            if data['missing'].strip()
                            else [])}


@s.func.flow
def _cover(test_file):
    assert os.path.isfile(test_file), 'no such file: {}'.format(test_file)
    try:
        module_name = s.shell.module_name(s.test.code_file(test_file))
    except AssertionError:
        return
    else:
        text = s.shell.run('py.test --cov-report term-missing', test_file, '--cov', module_name)
        return _parse_coverage(module_name, text)
