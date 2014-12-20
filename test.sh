#!/bin/bash
set -o pipefail
ag -g ".*\.py$"|grep -v -e test_ -e __init__ -e setup.py|xargs python -m doctest
ag -g ".*\.py$"|grep -v -e test_ -e __init__ -e setup.py|xargs python3 -m doctest
ag -g "test_.*/fast/.*\.py$"|xargs py.test -xvv --tb native
ag -g "test_.*/fast/.*\.py$"|xargs py.test3 -xvv --tb native
ag -g "test_.*/slow/.*\.py$"|xargs -n 1 -P 0 py.test -xvv --tb native
ag -g "test_.*/slow/.*\.py$"|xargs -n 1 -P 0 py.test3 -xvv --tb native
