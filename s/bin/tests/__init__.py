from __future__ import print_function, absolute_import
from s.bin.tests import auto
from s.bin.tests import cover
import argh


def main():
    argh.dispatch_commands([auto.auto,
                            cover.cover])
