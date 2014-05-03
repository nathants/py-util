import s


def test_filter_test_files1():
    val = [
        ['/tmp/tdHuDDvMYt', ['.git', 'test_module'], []],
        ['/tmp/tdHuDDvMYt/test_module', ['fast'], ['__init__.py']],
        ['/tmp/tdHuDDvMYt/test_module/fast', [], ['__init__.py', '__init__.pyc', 'foo.py']],
    ]
    assert s.test._filter_test_files(val) == ['/tmp/tdHuDDvMYt/test_module/fast/__init__.py',
                                              '/tmp/tdHuDDvMYt/test_module/fast/foo.py']
