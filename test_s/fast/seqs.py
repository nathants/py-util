import s


def test_list_walk():
    fn = lambda x: isinstance(x, int) and x + 1 or x
    assert s.seqs.walk([1, [2, 3]], fn) == [2, [3, 4]]


def test_dict_walk():
    fn = lambda x: isinstance(x, int) and x + 1 or x
    assert s.seqs.walk({1: {2: 3}}, fn) == {2: {3: 4}}


def test_dict_replace_kv_walk():
    fn = lambda x: x == (2, 3) and ('!', '?') or x
    assert s.seqs.walk({1: {2: 3}}, fn) == {1: {'!': '?'}}


def test_list_concat():
    assert s.seqs.concat([1], [2], [3]) == (1, 2, 3)


def test_list_flatten():
    assert s.seqs.flatten([1, [2, [3, 4]]]) == (1, 2, 3, 4)


def test_dict_flatten():
    assert set(s.seqs.flatten({1: {2: 3}})) == {1, 2, 3}
