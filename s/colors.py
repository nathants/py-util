from __future__ import absolute_import
import functools


_pairs = zip(['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
             range(31, 38))


def _make_color(code, text):
    return "\033[{}m{}\033[0m".format(code, text)


for _color, _num in _pairs:
    locals()[_color] = functools.partial(_make_color, _num)
