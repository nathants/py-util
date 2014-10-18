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


def _header(data, highlight):
    val = '-' * (1 + len(data['stack']))
    if data['direction'] == 'out':
        val = val[1:] + '<'
    else:
        val += '>'
    name = data['name']
    if highlight:
        val = s.colors.green(val)
        name = s.colors.green(name)
    return val + '\n ' + name


def _body(data, hide_keys, pretty, max_lines):
    val = []
    for k, v in s.dicts.drop(data, *hide_keys).items():
        if not v:
            continue
        elif isinstance(v, (list, dict)) and pretty:
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


def _visualize(index, path, datas, hidden_keys, max_lines, pair=False, pretty=True):
    if pair:
        vals = _pair(index, datas)
    else:
        vals = [(datas[index], True)]
    output = ['path: {}'.format(path),
              'index: {}'.format(index)]
    for data, highlight in vals:
        output += ['',
                   _header(data, highlight),
                   _body(data, hidden_keys, pretty, max_lines)]
    return '\n'.join(output)


def _pair(index, datas):
    data = datas[index]
    inward = datas[index]['direction'] == 'in'
    if inward:
        datas = datas[index + 1:]
    else:
        datas = reversed(datas[:index])
    for pair in datas:
        match_names = pair['name'] == data['name']
        match_stack = pair['stack'] == data['stack'][:-1] or pair['stack'][:-1] == data['stack']
        if match_names and match_stack:
            break
    vals = [(pair, False), (data, True)]
    if inward:
        vals = reversed(vals)
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

"""


def _print(t, text, wait=False):
    print(t.clear)
    print(text)
    if wait:
        pager.getch()


def _app(t, path):
    with open(path) as _file:
        datas = [json.loads(x) for x in _file.read().splitlines()]

    pair = False
    pretty = True
    index = 0
    max_lines_increment = 10
    max_lines_high = 1e10
    max_lines = max_lines_low = 10
    hidden_keys = _hidden_keys = ['direction', 'name', 'fntype', 'time', 'stack', 'cwd']

    while True:
        _print(t, _visualize(index, path, datas, hidden_keys, max_lines, pair, pretty))
        char = pager.getch()
        if char == 'g':
            char += pager.getch()
        with t.location(0, 0):
            if char == 'q':
                return
            elif char == '?':
                _print(t, _help, True)
            elif char == 'j':
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
    visualizer for data flow debug logs created with s.func.* decorators and s.log.setup().

    when called with no args, uses the latest debug log.

    when called with one arg, uses that as a file name, and then falls back to re.search.
    """

    vals = s.shell.files('/tmp', True)
    vals = [x for x in vals if x.endswith(':debug.log')]
    vals = sorted(vals, key=lambda x: os.stat(x).st_mtime, reverse=True)

    if file_or_regex:
        if os.path.isfile(file_or_regex):
            path = file_or_regex
        elif os.path.isfile(os.path.join('/tmp', file_or_regex)):
            path = os.path.join('/tmp', file_or_regex)
        else:
            for val in vals:
                if re.search(file_or_regex, val):
                    path = val
                    break
            print('nothing matched regex: {}'.format(file_or_regex))
            sys.exit(1)
    else:
        try:
            path = vals[0]
        except:
            print('no debug logs found')
            sys.exit(1)

    t = blessed.Terminal()
    with t.fullscreen():
        with t.hidden_cursor():
            print(t.clear)
            _app(t, path)


def main():
    argh.dispatch_command(_main)
