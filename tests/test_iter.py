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
    assert [('0-9', [3, 7]), ('10-19', [10, 11, 12]), ('20-29', [20, 21, 22]), ('30-39', [31])] \
        == util.iter.histogram([3, 7, 10, 11, 12, 20, 21, 22, 31], size=10, accumulate=True)
    assert [('0-9', 2), ('10-19', 3), ('20-29', 3), ('30-39', 1)] \
        == util.iter.histogram([{'v': 3}, {'v': 7}, {'v': 10}, {'v': 11}, {'v': 12}, {'v': 20}, {'v': 21}, {'v': 22}, {'v': 31}], size=10, key=lambda x: x['v'])
    assert [('0-9', 2), ('10-19', 3), ('20-29', 3), ('30-39', 1)] \
        == util.iter.histogram([3, 7, 10, 11, 12, 20, 21, 22, 31], size=10)
    assert [('0-9', 2), ('10-29', 6), ('30-39', 1)] \
        == util.iter.histogram([3, 7, 10, 11, 12, 20, 21, 22, 31], size=10, exponential=True)
