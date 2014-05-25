import s


def setup_module():
    s.log.setup(level='debug', short=True)


def test_timer():
    with s.time.timer() as t:
        pass
    assert t['seconds'] > 0
