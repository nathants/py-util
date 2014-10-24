from __future__ import print_function, absolute_import
import s
import types


def _missing_funcs(test_file):
    test_module = s.shell.module_name(test_file)
    code_module = s.shell.module_name(s.test.code_file(test_file))
    return [fn for fn in _list_functions(code_module)
            if not any(test_fn.endswith('_' + fn)
                       for test_fn in _list_functions(test_module))]


def _print_code_module_name(test_file):
    return s.func.thrush(
        test_file,
        s.test.code_file,
        s.shell.module_name,
        s.colors.yellow,
        print,
    )


def _print_cov_data(test_file):
    cov_data = s.test._cover(test_file)
    print(getattr(s.colors, 'green' if cov_data['percent'] == '100' else 'red')(cov_data['percent'] + '% '))
    if cov_data['missing']:
        missing_text = ' missing lines: '
        missing_count = 5
        missing_text += (', '.join(cov_data['missing'][:missing_count]) +
                         ('...' if len(cov_data['missing']) > missing_count else ''))
        print(missing_text)


def _print_missing_tests(test_file):
    missing_funcs = _missing_funcs(test_file)
    if missing_funcs:
        print(' missing tests:')
        for name in missing_funcs:
            print('  test_*_{name}'.format(**locals()))


def _print_missing_test_files():
    missing_test_files = []
    for code_file in s.test.code_files():
        try:
            s.test.test_file(code_file)
        except AssertionError:
            missing_test_files.append(s.test._test_file(s.shell.rel_path(code_file)))
    if missing_test_files:
        print(s.colors.yellow('missing test files:'))
        for test_file in missing_test_files:
            print('', test_file)


def _list_functions(module_name):
    return [k
            for k, v in __import__(module_name, fromlist='*').__dict__.items()
            if isinstance(v, types.FunctionType)
            and v.__module__ == module_name]


def cover(grep_module=None):
    for test_file in s.test.fast_test_files():
        try:
            s.test.code_file(test_file)
        except AssertionError:
            continue

        module = s.shell.module_name(s.test.code_file(test_file))
        if grep_module and grep_module not in module:
            continue

        _print_code_module_name(test_file)
        _print_cov_data(test_file)
        _print_missing_tests(test_file)

    if not grep_module:
        _print_missing_test_files()
