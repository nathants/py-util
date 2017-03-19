import util.iter


def test_percentile():
    assert 97 == util.iter.percentile(range(1, 101), 97)
    assert 3 == util.iter.percentile(range(1, 101), 3)

def test_partition_by():
    assert [(0, 0, 0), (1, 1,), (2,)] == [tuple(x) for x in util.iter.partition_by([0, 0, 0, 1, 1, 2], lambda x: x)]


def test_group_by():
    assert [(0, [0, 2]), (1, [1, 3])] == util.iter.groupby(range(4), lambda x: x % 2)


def test_nwise():
    assert [(0, 1), (1, 2), (2, 3)] == list(util.iter.nwise(range(4), 2))
    assert [(0, 1, 2), (1, 2, 3)] == list(util.iter.nwise(range(4), 3))

def test_ichunk():
    assert [(0, 1), (2, 3), (4,)] == [tuple(x) for x in util.iter.ichunk(range(5), 2)]
    assert [(0, 1, 2), (3, 4)] == [tuple(x) for x in util.iter.ichunk(range(5), 3)]
    assert [(0,)] == [tuple(x) for x in util.iter.ichunk(range(1), 3)]

def test_chunk():
    assert [[0, 1], [2, 3], [4]] == list(util.iter.chunk(range(5), 2))
    assert [[0, 1, 2], [3, 4]] == list(util.iter.chunk(range(5), 3))
    assert [[0]] == list(util.iter.chunk(range(1), 3))


def test_chunks():
    assert [(0, 1, 2), (3, 4, 5)] == list(util.iter.chunks(range(6), 2))
    assert [(0, 1, 2), (3, 4)] == list(util.iter.chunks(range(5), 2))
    assert [(0, 1), (2, 3)] == list(util.iter.chunks(range(4), 2))
    assert [(0,), (1,)] == list(util.iter.chunks(range(2), 2))
    assert [(0,), (1,)] == list(util.iter.chunks(range(2), 3))

def test_histogram():
    assert [('1-10', 1), ('11-20', 3), ('21-30', 2)] == util.iter.histogram([10, 11, 12, 21, 22, 31], size=10)
    assert [('1-10', 1), ('11-30', 5)] == util.iter.histogram([10, 11, 12, 21, 22, 31], size=10, exponential=True)
