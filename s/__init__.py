from __future__ import print_function, absolute_import
from s.hacks import ModuleRedirector
ModuleRedirector(__name__, lambda x: __import__('s.{}'.format(x), fromlist='*'))
