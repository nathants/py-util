import itertools
import base64
import re
import util.colors


_color = re.compile(r'\$(red|green|blue|cyan|yellow|magenta)\(')


def color(text):
    while True:
        try:
            head, color, tail = _color.split(text, 1)
        except ValueError:
            return text
        color_me, tail = tail.split(')', 1)
        text = head + getattr(util.colors, color)(color_me) + tail


_rm_color = re.compile(r'\x1b[^m]*m')


def rm_color(text):
    return _rm_color.sub('', text)


def indent(text, spaces):
    fn = lambda x: ' ' * spaces + x
    return '\n'.join(map(fn, text.splitlines()))


def unindent(text, spaces):
    if spaces == 0:
        return text
    def fn(x):
        assert set(x[:spaces]) == {' '}, 'cannot unindent {spaces} spaces: {x}'.format(**locals())
        return x[spaces:]
    return '\n'.join(map(fn, text.splitlines()))


def abbrev(text, max_len):
    if len(text) > max_len:
        text = text[:max_len] + ' ...'
    return text


def align(text, sep=None, lines=False):
    rows = [x.split(sep) for x in text.splitlines()]
    sizes = [max(len(rm_color(x)) for x in row) for row in itertools.zip_longest(*rows, fillvalue='')]
    rows = [[col.ljust(size + len(col) - len(rm_color(col))) for size, col in zip(sizes, cols)] for cols in rows]
    return '\n'.join((' | ' if lines else ' ').join(r).rstrip() for r in rows)

def b64_encode(x):
    return base64.b64encode(bytes(x, 'utf-8')).decode('utf-8')


def b64_decode(x):
    return base64.b64decode(bytes(x, 'utf-8')).decode('utf-8')
