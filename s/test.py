from __future__ import absolute_import, print_function
import zmq
import re
import sys
import time
import types
import traceback
import os
import s
import itertools
import six


@s.trace.glue
def code_file(test_file):
    assert os.path.isfile(test_file), 'no such test_file: {}'.format(test_file)
    test_file_rel_path = s.shell.rel_path(test_file)
    root = test_file.split(test_file_rel_path)[0]
    path = os.path.join(root, _code_file(test_file_rel_path))
    assert os.path.isfile(path), 'no such code_file: {}'.format(path)
    return path


@s.trace.glue
def test_file(code_file):
    assert os.path.isfile(code_file), 'no such code_file: {}'.format(code_file)
    code_file_rel_path = s.shell.rel_path(code_file)
    root = code_file.split(code_file_rel_path)[0]
    path = os.path.join(root, _test_file(code_file_rel_path))
    assert os.path.isfile(path), 'no such test_file: {}'.format(path)
    return path


@s.trace.logic
def _test_file(code_file):
    assert not code_file.startswith('/'), 'code_file is not relative path from project root: {}'.format(code_file)
    assert code_file.endswith('.py'), 'code_file does not end with .py: {}'.format(code_file)
    val = code_file.split('/')
    val[0] = 'test_{}'.format(val[0])
    val = val[:1] + ['fast'] + val[1:]
    val = '/'.join(val)
    return val


@s.trace.logic
def _code_file(test_file):
    assert not test_file.startswith('/'), 'test_file is not relative path from project root: {}'.format(test_file)
    assert test_file.endswith('.py'), 'test_file does not end with .py: {}'.format(test_file)
    val = test_file.split('/')
    val[0] = val[0].replace('test_', '')
    val.pop(1)
    val = '/'.join(val)
    return val


@s.trace.logic
def _git_root(climb_data):
    climb_data = list(climb_data)
    val = [path for path, dirs, _ in climb_data if '.git' in dirs]
    assert val, 'didnt find git root from: {}'.format(climb_data[0][0])
    return val[0]


@s.trace.logic
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


@s.trace.logic
def _filter_fast_test_files(paths):
    return [x for x in paths
            if 'fast' in x.split('/')
            or 'unit' in x.split('/')]


@s.trace.logic
def _filter_slow_test_files(paths):
    return [x for x in paths
            if 'slow' in x.split('/')
            or 'integration' in x.split('/')]


@s.trace.logic
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


@s.trace.glue
def python_packages():
    return s.func.pipe(
        s.shell.walk(),
        _python_packages,
    )


@s.trace.logic
def _python_packages(walk_data):
    walk_data = list(walk_data)
    return [path
            for path, _, files in walk_data
            if os.path.basename(path) in walk_data[0][1]
            and '__init__.py' in files]


@s.trace.io
def _mapwalk(dirs):
    return [s.shell.walk(x) for x in dirs]


@s.trace.io
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


@s.trace.io
def _run_test(path, name, test):
    _bak = s.trace._state.get('_stack')
    s.trace._state['_stack'] = None # stub out _stack, since its used *here* as well
    try:
        with s.time.timer() as t:
            try:
                test()
                val = False
            except:
                tb = traceback.format_exc()
                try:
                    # TODO this is why fail is slower than success for red/green light
                    # TODO this should be async, and not block feedback to the websocket
                    val = _pytest_insight(path, name)
                except:
                    val = tb + '\nFAILED to reproduce test failure in py.test, go investigate!' + traceback.format_exc()
        return _result(val, '{}:{}()'.format(path, name), round(t['seconds'], 3))
    finally:
        s.trace._state['_stack'] = _bak


@s.trace.glue
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
    return s.func.pipe(
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


@s.trace.glue
def _pytest_insight(test_file, query):
    assert os.path.isfile(test_file), 'no such file: {}'.format(test_file)
    val = s.shell.run('py.test -qq -k', query, test_file, warn=True)
    assert not any(x.startswith('ERROR: file not found:') for x in val['output'].splitlines())
    assert not any(x.startswith('ERROR: not found:') for x in val['output'].splitlines())
    assert val['exitcode'] != 0
    return _format_pytest_output(val['output'])


@s.trace.logic
def _linenum(text):
    return [int(x.split(', line ')[-1].split(',')[0])
            for x in text.splitlines()
            if 'File "<string>"' in x][-1]


@s.trace.glue
def _test_all(paths):
    return [_test(x) for x in paths]


@s.trace.glue
def all_test_files():
    return s.func.pipe(
        s.shell.climb(),
        _git_root,
        s.shell.walk,
        _filter_test_files,
        sorted,
    )


@s.trace.glue
def slow_test_files():
    return s.func.pipe(
        all_test_files(),
        _filter_slow_test_files,
    )


@s.trace.glue
def fast_test_files():
    return s.func.pipe(
        all_test_files(),
        _filter_fast_test_files,
    )


@s.trace.glue
def code_files():
    return s.func.pipe(
        s.shell.climb(),
        _git_root,
        s.shell.walk,
        _python_packages,
        _mapwalk,
        _filter_code_files,
        sorted,
    )


@s.trace.glue
def run_slow_tests_once():
    if six.PY2:
        pytest = 'py.test'
    else:
        pytest = 'py.test3'
    result = s.shell.run(pytest, '-x --tb native', *slow_test_files(), warn=True)
    if result['exitcode'] != 0:
        text = _format_pytest_output(result['output'])
        return [[{'result': text, 'path': 'test_*/slow/*.py', 'seconds': 0}]]


@s.trace.glue
def run_fast_tests_once(modules=None):
    result = s.shell.run('py.test -x --tb native', *fast_test_files(), warn=True)
    if result['exitcode'] != 0:
        text = _format_pytest_output(result['output'])
        return [[{'result': text, 'path': 'test_*/fast/*.py', 'seconds': 0}]]


@s.trace.glue
def run_lightweight_tests_once(modules=None):
    for x in modules or []:
        sys.modules.pop(x, None)
    return _test_all(fast_test_files())


@s.trace.logic
def _drop_seconds(test_datas):
    if test_datas:
        return [s.dicts.drop(y, 'seconds')
                for x in test_datas
                for y in x]
    else:
        return test_datas


def _modules_to_reload():
    with s.shell.climb_git_root():
        return [s.shell.module_name(x)
                for x in s.shell.walk_files(python_packages(),
                                            lambda f: (f.endswith('.py')
                                                       and not f.startswith('.')
                                                       and '_flymake' not in f))]


def _run_bg_tests(fn, result_route):
    trigger_route = s.sock.new_ipc_route()
    def main():
        trigger_puller = s.sock.bind('pull', trigger_route)
        result_pusher = s.sock.connect('push', result_route)
        @trigger_puller.on_recv
        def trigger_on_recv(msg):
            print('trigger on recv')
            result_pusher.send('fake result')
        s.async.ioloop().start()
    s.proc.new(main)
    trigger_pusher = s.sock.connect('push', trigger_route, sync=True)
    def trigger(*args):
        with s.exceptions.ignore(zmq.Again):
            print('call trigger')
            trigger_pusher.send('')
    return trigger


def run_tests_auto(output_route):
    results_route = s.sock.new_ipc_route()
    trigger_fast = _run_bg_tests(run_lightweight_tests_once, results_route)

    watch_subber = s.sock.connect('sub', s.shell.watch_files())
    @watch_subber.on_recv
    def watcher_on_recv(_):
        print('file system changed')
        trigger_fast()

    results_puller = s.sock.bind('pull', results_route)
    @results_puller.on_recv
    def results_on_recv(msg):
        print('results received', msg)

    s.async.ioloop().start()


@s.trace.glue
def _run_tests_auto(pytest):
    files_changed = s.shell.watch_files()

    trigger_slow, results_slow = _run_bg_tests(run_slow_tests_once)
    trigger_fast, results_fast = _run_bg_tests(run_fast_tests_once if pytest else run_lightweight_tests_once)

    modules = _modules_to_reload()
    slow_tests_output = []
    fast_tests_output = []

    slow_changed = lambda: results_slow() != slow_tests_output
    fast_changed = lambda: _drop_seconds(results_fast()) != _drop_seconds(fast_tests_output) # seconds causes useless redraws
    while True:
        if files_changed() or slow_changed() or fast_changed():
            trigger_slow()
            trigger_fast(modules)

            slow_tests_output = results_slow()
            fast_tests_output = results_fast()

            yield fast_tests_output + slow_tests_output

        time.sleep(.01)


@s.trace.logic
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


@s.trace.glue
def _cover(test_file):
    assert os.path.isfile(test_file), 'no such file: {}'.format(test_file)
    try:
        module_name = s.shell.module_name(s.test.code_file(test_file))
    except AssertionError:
        return
    else:
        text = s.shell.run('py.test --cov-report term-missing', test_file, '--cov', module_name)
        return _parse_coverage(module_name, text)
