import util.seqs


def test_split_with():
    fn = lambda x: x != 2
    assert util.seqs.split_with(fn, range(4)) == [[0, 1], [2, 3]]


def test_list_walk():
    fn = lambda x: isinstance(x, int) and x + 1 or x
    assert util.seqs.walk(fn, [1, [2, 3]]) == [2, [3, 4]]


def test_dict_walk():
    fn = lambda x: isinstance(x, int) and x + 1 or x
    assert util.seqs.walk(fn, {1: {2: 3}}) == {2: {3: 4}}


def test_dict_walk_transform():
    fn = lambda x: isinstance(x, tuple) and len(x) == 2 and ['{}!!'.format(x[0]), x[1]] or x
    assert util.seqs.walk(fn, {1: {2: 3}}) == {'1!!': {'2!!': 3}}


def test_dict_replace_kv_walk():
    fn = lambda x: x == (2, 3) and ('!', '?') or x
    assert util.seqs.walk(fn, {1: {2: 3}}) == {1: {'!': '?'}}


def test_list_concat():
    assert util.seqs.concat([1], [2], [3]) == (1, 2, 3)


def test_list_flatten():
    assert util.seqs.flatten([1, [2, [3, 4]]]) == (1, 2, 3, 4)


def test_dict_flatten():
    assert set(util.seqs.flatten({1: {2: 3}})) == {1, 2, 3}


def test_value():
    assert util.seqs.flatten(1) == (1,)
