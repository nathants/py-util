from __future__ import absolute_import, print_function
import blessed
import s
import s.sock # init zmq
import s.bin.tests.server
import s.bin.tests.lib


_max_seconds = .01


def _view(test_data):
    failures = [x['result'] for x in test_data if x['result']]
    slows = ['{} ran in {}s, max is {}s'.format(x['path'],
                                                x['seconds'],
                                                _max_seconds)
             for x in test_data
             if x['seconds'] > _max_seconds
             and not x['result']]
    color = s.colors.red if failures else s.colors.yellow if slows else s.colors.green
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


def _file_name(x):
    return x['path'].split(':')[0]


def _match(a, b):
    return _file_name(a) == _file_name(b[0][0])


def _one_and_all_passed(name, data):
    return (name == 'one'
            and data
            and data[0]
            and not any(y['result']
                        for x in data
                        for y in x))


def _when_dict_set_result_to_false(data):
    def fn(x):
        return (isinstance(x, dict)
                and x['result']
                and _match(x, data)
                and s.dicts.set(x, 'result', False)
                or x)
    return fn


def _app(terminal, pytest):
    route = s.sock.route()
    @s.async.coroutine
    def main():
        state = {}
        s.bin.tests.server.start()
        s.bin.tests.lib.run_tests_auto(route)
        with s.sock.bind('pull', route) as sock:
            while True:
                name, data = yield sock.recv()
                state[name] = data
                if 'fast' in state and _one_and_all_passed(name, data):
                    state['fast'] = s.seqs.walk(_when_dict_set_result_to_false(data), state['fast'])
                all_data = sum(state.values(), ())
                text = '\n'.join(map(_view, all_data)) or s.colors.green('tests passed')
                _print(terminal, text)
                s.bin.tests.server.send(all_data)
    s.async.run_sync(main)
