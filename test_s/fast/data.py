import s
import json
import pytest
import mock


def test_unicode_synonymous_with_str():
    assert s.data.freeze({u'a': 'b'}) == {'a': 'b'}
    assert s.data.freeze(u'asdf') == 'asdf'


def test_setitem_freeze():
    with pytest.raises(Exception):
        s.data.freeze({'a': 1})['a'] = 2


def test_pop_freeze():
    with pytest.raises(Exception):
        s.data.freeze({'a': 1}).pop()


def test_popitem_freeze():
    with pytest.raises(Exception):
        s.data.freeze({'a': 1}).popitem()


def test_update_freeze():
    with pytest.raises(Exception):
        s.data.freeze({'a': 1}).update()


def test_clear_freeze():
    with pytest.raises(Exception):
        s.data.freeze({'a': 1}).clear()


def test_append_freeze():
    with pytest.raises(ValueError):
        s.data.freeze([]).append(1)


def test_getitem_freeze():
    assert 1 == s.data.freeze({'a': 1})['a']


def test_set_freeze():
    x = {1, 2, 3}
    y = s.data.freeze(x)
    x.add(4)
    assert y == {1, 2, 3}


def test_nested_freeze():
    x = {1}
    y = s.data.freeze({'val': x})
    x.add(2)
    assert len(y['val']) == 1


def test_list_freeze():
    x = [1, 2, 3]
    y = s.data.freeze(x)
    x.append(4)
    assert y == [1, 2, 3]


def test_dont_refreeze():
    fn = s.data.freeze
    with mock.patch.object(s.data, 'freeze') as m:
        m.side_effect = fn
        x = [1, 2, 3]
        assert m.call_count == 0
        x = s.data.freeze(x)
        assert m.call_count == 4 # called once for [] and once for each element
        s.data.freeze(x)
        assert m.call_count == 5 # called once for [] and shortcircuit
        s.data.freeze(x)
        assert m.call_count == 6 # called once for [] and shortcircuit


def test_equality():
    assert s.data.freeze([1, 2]) == [1, 2]
    assert s.data.freeze((1, 2)) == (1, 2)
    assert not s.data.freeze([1, 2]) == (x for x in range(1, 3))


def test_prod_failure_binary_that_cant_decode_utf8():
    x = b'\x00d\x0f\x9c\r'
    assert x == s.func.pipe(x,
                            s.data.jsonify,
                            json.dumps,
                            json.loads,
                            s.data.a2b)
