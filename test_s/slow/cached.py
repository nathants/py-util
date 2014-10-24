import s


def test_disk():
    state = {'val': 0}
    @s.cached.disk
    def fn():
        state['val'] += 1
    fn.clear_cache()
    fn(), fn(), fn()
    assert state['val'] == 1
