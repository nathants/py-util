import s


def test_get():
    assert s.dicts.get({1: {2: 3}}, 1, 2) == 3


def test_put():
    assert s.dicts.put({}, 3, 1, 2) == {1: {2: 3}}


def test_merge():
    assert s.dicts.merge({1: {2: 3}},
                         {1: {4: 5}}) == {1: {2: 3,
                                              4: 5}}

def test_merge_simple():
    assert s.dicts.merge({1: 2},
                         {1: 3, 2: 4}) == {1: 3, 2: 4}


def test_merge_iterables():
    assert s.dicts.merge({1: {2: [1, 2]}},
                         {1: {2: [3, 4]}}) == {1: {2: [1, 2, 3, 4]}}


def test_concatable():
    assert s.dicts._concatable([], [])
    assert s.dicts._concatable((), ())
    assert not s.dicts._concatable((), [])
    assert not s.dicts._concatable([], 1)


def test_only():
    assert s.dicts.only({1: True, 2: True, 3: True}, 1, 2) == {1: True, 2: True}


def test_only_padded():
    assert s.dicts.only({1: True}, 1, 2, 3, padded=None) == {1: True, 2: None, 3: None}

def test_drop():
    assert s.dicts.drop({1: 1, 2: 2}, 1) == {2: 2}
