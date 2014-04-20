from __future__ import print_function
import types
import traceback
import collections
import os
import s
import itertools as i


@s.fn.logic
def _test_file(_code_file):
    assert not _code_file.startswith('/')
    assert _code_file.endswith('.py')
    val = _code_file.split('/')
    val[0] = 'test_{}'.format(val[0])
    val = val[:1] + ['fast'] + val[1:]
    val = '/'.join(val)
    return val


@s.fn.logic
def _code_file(_test_file):
    val = _test_file.split('/')
    val[0] = val[0].replace('test_', '')
    val.pop(1)
    val = '/'.join(val)
    return val


@s.fn.glue
def _climb(where='.'):
    val = []
    with s.shell.cd():
        while True:
            val.append([os.getcwd(), s.shell.dirs(), s.shell.files()])
            if os.getcwd() == '/':
                break
            os.chdir('..')
    return val


@s.fn.glue
def _walk(where='.'):
    with s.shell.cd('.'):
        return list(os.walk(where))


@s.fn.logic
def _git_root(climb_data):
    climb_data = list(climb_data)
    val = [path for path, dirs, _ in climb_data if '.git' in dirs]
    assert val, 'didnt find git root from: {}'.format(climb_data[0][0])
    return val[0]


@s.fn.logic
def _filter_test_files(walk_data):
    return [os.path.join('/'.join(path.split('/')[-2:]), f)
            for path, _, files in walk_data
            for f in files
            if f.endswith('.py')
            and len(path.split('/')) >= 2
            and path.split('/')[-2].startswith('test_')
            and path.split('/')[-1] == 'fast']


@s.fn.logic
def _filter_code_files(walk_datas):
    return [os.path.join(path, name)
            for data in walk_datas
            for path, _, files in data
            for name in files]


@s.fn.logic
def _python_packages(walk_data):
    walk_data = list(walk_data)
    return [os.path.basename(path)
            for path, _, files in walk_data
            if os.path.basename(path) in walk_data[0][1]
            and '__init__.py' in files]


@s.fn.flow
def all_test_files():
    return s.fn.thread(
        _climb(),
        _git_root,
        _walk,
        _filter_test_files
    )


@s.fn.flow
def all_code_files():
    return s.fn.thread(
        _climb(),
        _git_root,
        _walk,
        _python_packages,
        lambda x: map(os.walk, x),
        _filter_code_files,
    )


@s.fn.glue
def _collect_tests(test_file):
    keep = ['<Function']
    text = s.shell.run('py.test --collect-only', test_file)
    return [x.strip() for x in text.splitlines()
            if any(x.strip().startswith(y) for y in keep)]


@s.fn.logic
def _is_test(k, v):
    return (k.startswith('test') and
            isinstance(v, types.FunctionType))


@s.fn.glue
def _exec_file(path):
    module = {}
    with open(path) as fio:
        text = fio.read()
    exec(text, globals(), module)
    return module, text


@s.fn.flow
def _test(test_file):
    assert test_file.endswith('.py') and not test_file.startswith('/')
    name = test_file.replace('.py', '').replace('/', '.')
    module = __import__(name, fromlist='*')
    try:
        for k, v in module.__dict__.items():
            if k not in ['__builtins__', '__builtin__']:
                if _is_test(k, v):
                    # todo time the tests, time each file, time the whole suite. print everything. enforce shit?
                    v()
        result = False
    except:
        tb = traceback.format_exc().splitlines()
        try:
            result = _pytest_insight(module.__file__.replace('.pyc', '.py'), k)
        except:
            result = tb
    return collections.namedtuple('test', 'result path')(result, test_file)


@s.fn.flow
def _pytest_insight(test_file, query):
    val = s.shell.run('py.test -qq -k', query, test_file, warn=True)
    assert not any(x.startswith('ERROR: file not found:') for x in val.output.splitlines())
    assert not any(x.startswith('ERROR: not found:') for x in val.output.splitlines())
    assert os.path.isfile(test_file)
    assert val.exitcode != 0
    val = s.fn.thread(
        val.output,
        str.splitlines,
        reversed,
        lambda x: i.dropwhile(lambda y: y.startswith('===='), x),
        lambda x: i.takewhile(lambda y: not y.startswith('_____'), x),
        list,
        reversed,
        '\n'.join,
        lambda x: '\n{0}\n{1}\n{0}\n'.format('-' * 80, x),
    )
    return val.splitlines()


@s.fn.logic
def _linenum(text):
    return [int(x.split(', line ')[-1].split(',')[0])
            for x in text.splitlines()
            if 'File "<string>"' in x][-1]


@s.fn.flow
def _test_all(paths):
    return [_test(x) for x in paths]


@s.fn.flow
def run_tests_once():
    return s.fn.thread(
        all_test_files(),
        _test_all,
    )


@s.fn.flow
def run_tests_auto():
    return s.fn.thread(

    )
