import re
import s.colors


_color = re.compile(r'\$(red|green|blue|cyan|yellow|magenta)\(')


def color(text):
    while True:
        try:
            head, color, tail = _color.split(text, 1)
        except ValueError:
            return text
        color_me, tail = tail.split(')', 1)
        text = head + getattr(s.colors, color)(color_me) + tail


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
