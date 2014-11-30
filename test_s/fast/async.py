import s


def test_coroutine():
    state = []
    @s.async.coroutine
    def zero():
        for i in range(2):
            state.append(i)
            yield s.async.moment
    @s.async.coroutine
    def ten():
        zero()
        for i in range(10, 12):
            state.append(i)
            yield s.async.moment
    s.async.run_sync(ten)
    assert state == [0, 10, 1, 11]
