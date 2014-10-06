from __future__ import print_function, absolute_import
import s.bin.tests.auto
import s.bin.tests.cover
import argh


def main():
    argh.dispatch_commands([auto.auto,
                            cover.cover])
