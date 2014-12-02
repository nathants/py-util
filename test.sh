#!/bin/bash
set -o pipefail
ag -g "test_.*/fast/.*\.py$"|xargs py.test -xsvv --tb native
ag -g "test_.*/fast/.*\.py$"|xargs py.test3 -xsvv --tb native
ag -g ".*\.py$"|grep -v -e test_ -e __init__ -e setup.py|xargs python -m doctest
ag -g ".*\.py$"|grep -v -e test_ -e __init__ -e setup.py|xargs python3 -m doctest
