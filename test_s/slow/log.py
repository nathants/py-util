from __future__ import print_function, absolute_import
import s.log
import mock
import logging.handlers


def test__get_trace_path():
    s.log.setup.clear_cache()
    with mock.patch.object(logging.handlers, 'WatchedFileHandler') as m:
        s.log.setup()
    [[path], _] = m.call_args
    assert path.split('/')[-1].split(':')[:-2] == ['test_s.slow.log', 'test__get_trace_path']


def test_name__get_trace_path():
    s.log.setup.clear_cache()
    with mock.patch.object(logging.handlers, 'WatchedFileHandler') as m:
        s.log.setup(name='foo')
    [[path], _] = m.call_args
    assert path.split('/')[-1].split(':')[:-2] == ['foo', 'test_s.slow.log', 'test_name__get_trace_path']
