import s


def test_coroutine():
    state = []
    @s.async.coroutine
    def a():
        for i in range(3):
            state.append(i)
            yield s.async.sleep(1e-6)
        raise s.async.Return('a')
    @s.async.coroutine
    def b():
        for i in range(10, 13):
            state.append(i)
            yield s.async.sleep(1e-6)
        raise s.async.Return('b')
    @s.async.coroutine
    def main():
        result = yield [a(), b()]
        raise s.async.Return(result)
    assert s.async.run_sync(main) == ('a', 'b')
    assert state == [0, 10, 1, 11, 2, 12]
