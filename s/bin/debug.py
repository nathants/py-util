from __future__ import absolute_import, print_function
import sys
import re
import os
import argh
import pager
import s
import json
import pprint
import blessed


def _header(data, highlight=False):
    try:
        val = '-' * (1 + len(data['stack']))
    except:
        print('data:', data)
        raise
    if data['direction'] == 'out':
        val = val[1:] + '<'
    else:
        val += '>'
    if data['fntype'] in ['gen.send', 'gen.yield']:
        val = val + val[-1]
    if data['fntype'] == 'gen.send':
        val = val[1:]
    name = data['name']
    if highlight:
        val = s.colors.green(val)
    return val + '\n ' + name


def _body(data, hide_keys, pretty, max_lines):
    val = []
    for k, v in s.dicts.drop(data, hide_keys).items():
        if isinstance(v, (tuple, list, dict)) and pretty:
            v = pprint.pformat(v, width=1).splitlines()
            size = len(k) + 3
            if len(v) > max_lines:
                v = v[:max_lines]
                v[-1] += ' ...'
            v = v[:1] + [s.strings.indent(x, size) for x in v[1:]]
            v = '\n'.join(v)
        elif k != 'traceback':
            v = repr(v)
            max_chars = 160
            if len(v) > max_chars:
                v = v[:max_chars] + ' ...'
        val.append(' {}: {}'.format(k, v))
    return '\n'.join(val)


@s.schema.check(int, int, int, [dict])
def _visualize_flat(width, height, index, datas):
    datas = datas[index:index + height - 2]
    datas = [[_header(data).split('\n'), data] for data in datas]
    size = max(len(data) for (data, _), _ in datas)
    datas = [[x.ljust(size) + y, data] for (x, y), data in datas]
    size = max(len(x) for x, _ in datas) + 1
    datas = [[x.ljust(size) + ('args=' + str(data['args'])
                               if data.get('args') else
                               'value=' + str(data['value'])
                               if data.get('value')
                               else ''),
              data]
             for x, data in datas]
    datas = [[x + (' kwargs=' + str(data['kwargs'].items()) if data.get('kwargs') else ''),
              data]
             for x, data in datas]
    datas = [[x + (' traceback=' + data['traceback'].splitlines()[-1]
                   if data.get('traceback')
                   else ''),
              data]
             for x, data in datas]

    datas = [[x[:min(width - 1, 200)], data] for x, data in datas]
    datas[0] = [s.colors.green(datas[0][0]), datas[0][1]]
    return '\n'.join([x for x, _ in datas])


def _visualize_single(index, path, datas, hidden_keys, max_lines, pair, pretty):
    if not pair or datas[index]['fntype'] in ['gen.send', 'gen.yield']:
        vals = [(datas[index], True)]
    else:
        vals = _pair(index, datas)
    output = ['path: {}'.format(path),
              'index: {}'.format(index)]
    for data, highlight in vals:
        output += ['',
                   _header(data, highlight),
                   _body(data, hidden_keys, pretty, max_lines)]
    return '\n'.join(output)


def _visualize(width, height, index, path, datas, hidden_keys, max_lines, pair, pretty, flat):
    if flat:
        return _visualize_flat(width, height, index, datas)
    else:
        return _visualize_single(index, path, datas, hidden_keys, max_lines, pair, pretty)


def _pair(index, datas):
    data = datas[index]
    inward = datas[index]['direction'] == 'in'

    if inward:
        datas = datas[index + 1:]
    else:
        datas = reversed(datas[:index])

    for pair in datas:
        match_names = pair['name'] == data['name']
        opposite_directions = pair['direction'], data['direction'] == 'in', 'out'
        send_or_yield = pair['fntype'] in ['gen.send', 'gen.yield']
        if match_names and opposite_directions and not send_or_yield:
            break
    else:
        raise Exception('no pair found')
    vals = [(pair, False), (data, True)]
    if inward:
        vals = list(reversed(vals))
    return vals


_help = """

    q - quit
    j - next
    k - prev
    G - end
    gg - start
    p - show in/out pairs
    f - pretty format
    t - toggle truncate data
    l - show less data
    m - show more data
    a - show all data
    c - show cwd
    s - disable stack visualization
    f - flat mode

"""


def _print(t, text, wait=False):
    if not globals()['just_print']:
        print(t.clear)
    print(text)
    if wait:
        pager.getch()


def _app(t, path):
    with open(path) as f:
        datas = [json.loads(x) for x in f.read().splitlines()]

    pair = False
    pretty = True
    flat = False
    index = 0
    max_lines_increment = 10
    max_lines_high = 1e10
    max_lines = max_lines_low = 10
    hidden_keys = _hidden_keys = ['direction', 'name', 'time', 'stack', 'cwd']

    while True:
        _print(t, _visualize(t.width, t.height, index, path, datas, hidden_keys, max_lines, pair, pretty, flat))
        char = pager.getch()
        if char == 'g':
            char += pager.getch()
        with t.location(0, 0):
            if char == 'q':
                return
            elif char == 'f':
                flat = not flat
            elif char == '?':
                _print(t, _help, True)
            elif char == 'j':
                if flat and len(datas) - index < 3:
                    continue
                else:
                    index = min(index + 1, len(datas) - 1)
            elif char == 'k':
                index = max(index - 1, 0)
            elif char == 'G':
                index = len(datas) - 1
            elif char == 'gg':
                index = 0
            elif char == 'p':
                pair = not pair
            elif char == 'f':
                pretty = not pretty
            elif char == 't':
                max_lines = max_lines_low if max_lines == max_lines_high else max_lines_high
            elif char == 'l':
                max_lines = max(max_lines_low, max_lines - max_lines_increment)
            elif char == 'm':
                max_lines += max_lines_increment
            elif char == 'a':
                if hidden_keys == _hidden_keys:
                    hidden_keys = []
                else:
                    hidden_keys = _hidden_keys
            elif char == 'c':
                if 'cwd' in hidden_keys:
                    hidden_keys.remove('cwd')
                else:
                    hidden_keys.append('cwd')


@argh.arg('file_or_regex', nargs='?', default=None)
def _main(file_or_regex):
    """
    visualizer for data flow trace logs created with s.func.* decorators and s.log.setup().

    when called with no args, uses the latest trace log.

    when called with one arg, uses that as a file name, and then falls back to re.search.
    """
    vals = s.shell.files('/tmp', True)
    vals = [x for x in vals if x.endswith(':trace.log')]
    vals = sorted(vals, key=lambda x: os.stat(x).st_mtime, reverse=True)

    if file_or_regex:
        if os.path.isfile(file_or_regex):
            path = file_or_regex
        elif os.path.isfile(os.path.join('/tmp', file_or_regex)):
            path = os.path.join('/tmp', file_or_regex)
        else:
            for val in vals:
                if re.search(file_or_regex, val) and os.path.getsize(val) > 0:
                    path = val
                    break
            print('nothing matched regex: {}'.format(file_or_regex))
            sys.exit(1)
    else:
        for path in vals:
            if os.path.getsize(path) > 0:
                break
        else:
            print('no trace logs found')
            sys.exit(1)

    t = blessed.Terminal()
    if globals()['just_print']:
        _app(t, path)
    else:
        with t.fullscreen():
            with t.hidden_cursor():
                print(t.clear)
                _app(t, path)


def main():
    globals()['just_print'] = s.shell.override('--print')
    argh.dispatch_command(_main)
