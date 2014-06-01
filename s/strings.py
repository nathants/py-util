from __future__ import absolute_import
import re
import s


_color = re.compile(r'\$(red|green|blue|cyan|yellow|magenta)\(')


def color(text): # todo 'red(foo yellow(123) bar)' doesnt work right
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
    indenter = lambda x: ' ' * spaces + x
    return '\n'.join(map(indenter, text.splitlines()))
