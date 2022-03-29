import sys
import os

force = 'COLORS' in os.environ

def _make_color(code, text):
    if force or sys.stdout.isatty():
        return "\033[{}m{}\033[0m".format(code, text)
    else:
        return text

clear   = lambda text: _make_color(38, text)
red     = lambda text: _make_color(31, text)
green   = lambda text: _make_color(32, text)
yellow  = lambda text: _make_color(33, text)
blue    = lambda text: _make_color(34, text)
magenta = lambda text: _make_color(35, text)
cyan    = lambda text: _make_color(36, text)
white   = lambda text: _make_color(37, text)
