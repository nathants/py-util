from __future__ import print_function
import sys
import logging
import types
import traceback
import inspect
import pprint
import os
import s
import itertools as i



@s.fn.logic
def _test_file(_code_file):
    assert not _code_file.startswith('/')
    assert _code_file.endswith('.py')
    val = '-'.join(_code_file.replace('.py', '').split('/'))
    return 'tests/unit/test-{}.py'.format(val)


@s.fn.logic
def _code_file(_test_file):
    assert _test_file.startswith('tests/unit/test-')
    return _test_file.replace('tests/unit/test-', '').replace('-', '/')


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
    files = [files for path, _, files in walk_data if path.endswith('tests/unit')]
    assert files, 'didnt find /tests/unit'
    return ['tests/unit/{}'.format(x) for x in files[0]]


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
    return all([k.startswith('test'),
                isinstance(v, types.FunctionType)])


@s.fn.glue
def _exec_file(path):
    module = {}
    with open(path) as fio:
        text = fio.read()
    exec(text, globals(), module)
    return module, text


@s.fn.flow
def _test(test_file):
    module, text = _exec_file(test_file)
    try:
        for k, v in module.items():
            if _is_test(k, v):
                v()
        return False
    except:
        try:
            return _pytest_insight(test_file, k)
        except:
            return _normal_insight(test_file, text)


@s.fn.glue
def _normal_insight(test_file, text):
    tb = traceback.format_exc()
    linenum = _linenum(tb)
    line = text.splitlines()[linenum - 1].strip()
    _locals = pprint.pformat(inspect.trace()[-1][0].f_locals)
    return '\n{test_file}:{linenum}\n{line}\n{_locals}\n'.format(**locals())


@s.fn.glue
def _pytest_insight(test_file, query):
    val = s.shell.run('py.test -qq -k', query, test_file, warn=True)
    assert val.exitcode != 0
    return s.fn.thread(
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


@s.fn.logic
def _linenum(text):
    return [int(x.split(', line ')[-1].split(',')[0])
            for x in text.splitlines()
            if 'File "<string>"' in x][-1]


@s.fn.glue
def _climb_find_abspath(path):
    with s.shell.cd():
        while True:
            _path = os.path.abspath(path)
            if os.path.isfile(_path):
                return _path
            assert os.getcwd() != '/', 'didnt find abspath after climbing to root'
            os.chdir('..')


@s.fn.flow
def climb_and_test(test_file):
    return s.fn.thread(
        test_file,
        _climb_find_abspath,
        _test,
    )


@s.fn.flow
def run_tests_once():
    return s.fn.thread(
        all_test_files(),
        lambda x: [climb_and_test(y) for y in x],
    )


@s.fn.flow
def run_tests_auto():
    return s.fn.thread(

    )



if __name__ == '__main__':

    s.log.setup(
        # level='debug',
        pprint=True,
        short=True
    )

    logging.info(climb_and_test('tests/int/test-s-test.py'))
    # print(run_tests_once())
