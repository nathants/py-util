import util.time
import time


def test_timer():
    with util.time.timer() as t:
        time.sleep(1e-6)
    assert t['seconds'] > 0
