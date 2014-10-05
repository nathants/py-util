from __future__ import print_function, absolute_import
from s.bin.tests import auto as _auto
from s.bin.tests import cover as _cover
import s


def auto():
    _auto.main()


def cover():
    _cover.main()

def main():
    s.shell.dispatch_commands(globals(), __name__)
