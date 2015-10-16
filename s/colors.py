import functools
import sys


being_piped = not sys.stdout.isatty()


_colors =['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']


_pairs = zip(_colors, range(31, 38))


def _make_color(code, text):
    if being_piped:
        return text
    else:
        return "\033[{}m{}\033[0m".format(code, text)


for _color, _num in _pairs:
    locals()[_color] = functools.partial(_make_color, _num)
