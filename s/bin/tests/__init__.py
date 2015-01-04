from __future__ import print_function, absolute_import
from s.bin.tests import auto
from s.bin.tests import cover
import argh
import s
import s.bin.tests.lib


def main():
    argh.dispatch_commands([auto.auto,
                            cover.cover,
                            s.bin.tests.lib.light_auto,
                            s.bin.tests.lib.slow_auto,
                            s.bin.tests.lib.one_auto])
