import s


def test_split_with():
    fn = lambda x: x != 2
    assert s.seqs.split_with(fn, range(4)) == [[0, 1], [2, 3]]


def test_list_walk():
    fn = lambda x: isinstance(x, int) and x + 1 or x
    assert s.seqs.walk(fn, [1, [2, 3]]) == [2, [3, 4]]


def test_dict_walk():
    fn = lambda x: isinstance(x, int) and x + 1 or x
    assert s.seqs.walk(fn, {1: {2: 3}}) == {2: {3: 4}}


def test_dict_walk_transform():
    fn = lambda x: isinstance(x, tuple) and len(x) == 2 and ['{}!!'.format(x[0]), x[1]] or x
    assert s.seqs.walk(fn, {1: {2: 3}}) == {'1!!': {'2!!': 3}}


def test_dict_replace_kv_walk():
    fn = lambda x: x == (2, 3) and ('!', '?') or x
    assert s.seqs.walk(fn, {1: {2: 3}}) == {1: {'!': '?'}}


def test_list_concat():
    assert s.seqs.concat([1], [2], [3]) == (1, 2, 3)


def test_list_flatten():
    assert s.seqs.flatten([1, [2, [3, 4]]]) == (1, 2, 3, 4)


def test_dict_flatten():
    assert set(s.seqs.flatten({1: {2: 3}})) == {1, 2, 3}


def test_value():
    assert s.seqs.flatten(1) == (1,)
