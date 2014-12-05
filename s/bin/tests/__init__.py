from __future__ import print_function, absolute_import
from s.bin.tests import auto
from s.bin.tests import cover
import argh
import s


def main():
    argh.dispatch_commands([auto.auto,
                            cover.cover,
                            s.test.one,
                            s.test.light_auto,
                            s.test.slow_auto,
                            s.test.slow,
                            s.test.fast,
                            s.test.light])
