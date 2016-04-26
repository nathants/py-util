import util.iter


def test_group_by():
    assert [(0, [0, 2]), (1, [1, 3])] == util.iter.groupby(range(4), lambda x: x % 2)


def test_nwise():
    assert [(0, 1), (1, 2), (2, 3)] == list(util.iter.nwise(range(4), 2))
    assert [(0, 1, 2), (1, 2, 3)] == list(util.iter.nwise(range(4), 3))


def test_chunk():
    assert [(0, 1), (2, 3), (4,)] == list(util.iter.chunk(range(5), 2))
    assert [(0, 1, 2), (3, 4)] == list(util.iter.chunk(range(5), 3))
    assert [(0, 1, 2)] == list(util.iter.chunk(range(5), 3, True))


def test_chunks():
    assert [(0, 1, 2), (3, 4, 5)] == list(util.iter.chunks(range(6), 2))
    assert [(0, 1, 2), (3, 4)] == list(util.iter.chunks(range(5), 2))
    assert [(0, 1), (2, 3)] == list(util.iter.chunks(range(4), 2))
    assert [(0,), (1,)] == list(util.iter.chunks(range(2), 2))
    assert [(0,), (1,)] == list(util.iter.chunks(range(2), 3))
