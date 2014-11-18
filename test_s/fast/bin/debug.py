import s.bin.debug


def test_in_pair():
    datas = [{u'direction': u'in',
              u'fntype': u'gen',
              u'name': u'flow:test_s.fast.func:a'},
             {u'direction': u'out',
              u'fntype': u'gen',
              u'name': u'flow:test_s.fast.func:a'}]
    [[a, highlight_a], [b, highlight_b]] = s.bin.debug._pair(0, datas)
    assert a['direction'] == 'in'
    assert b['direction'] == 'out'
    assert highlight_a and not highlight_b


def test_out_pair():
    datas = [{u'direction': u'in',
              u'fntype': u'gen',
              u'name': u'flow:test_s.fast.func:a'},
             {u'direction': u'out',
              u'fntype': u'gen',
              u'name': u'flow:test_s.fast.func:a'}]
    [[a, highlight_a], [b, highlight_b]] = s.bin.debug._pair(1, datas)
    assert a['direction'] == 'in'
    assert b['direction'] == 'out'
    assert highlight_b and not highlight_a
