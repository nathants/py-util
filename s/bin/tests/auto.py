from __future__ import absolute_import, print_function
import blessed
import s
import s.bin.tests.server
s.sock # init zmq


_max_seconds = .01


def _view(test_data):
    failures = [x['result'] for x in test_data if x['result']]
    slows = ['{} ran in {}s, max is {}s'.format(x['path'],
                                                x['seconds'],
                                                _max_seconds)
             for x in test_data
             if x['seconds'] > _max_seconds
             and not x['result']]
    color = s.colors.red if failures or slows else s.colors.green
    name = test_data[0]['path'].split(':')[0]
    val = color(name)
    for fail in failures + slows:
        val += '\n' + s.strings.indent(fail, 2)
    return val


def _print(terminal, text):
    print(terminal.clear)
    print(terminal.move(0, 0))
    print(text)
    print(terminal.move(0, 0)) # hide_cursor broken in multi-term in emacs


def auto(pytest=False):
    s.log.setup()
    terminal = blessed.Terminal()
    with terminal.fullscreen():
        with terminal.hidden_cursor():
            _app(terminal, pytest)


def _app(terminal, pytest):
    route = s.sock.route()
    @s.async.coroutine
    def main():
        s.bin.tests.server.start()
        s.test.run_tests_auto(route)
        with s.sock.bind('pull', route) as sock:
            while True:
                name, data = yield sock.recv()
                # TODO always print all the datas, not just this one. ie save them by name and then print all.
                s.bin.tests.server.send(data)
                text = ('\n'.join(map(_view, data))
                        or s.colors.green('tests passed'))
                _print(terminal, text)
    s.async.run_sync(main)
