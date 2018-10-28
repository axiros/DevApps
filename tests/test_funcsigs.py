

import pytest

from devapps.func_sigs import map_args_to_func_sig as mapf
from devapps.common import Exc
from functools import partial


def test_simple():
    a, kw = mapf(lambda a: a, [('a', 1)], {})
    assert a == (1,)
    assert kw == {}


def test_simple2():
    a, kw = mapf(lambda a, b='c': a, [('a', 1)], {})
    assert a == (1, 'c')
    assert kw == {}


def test_simple3():
    a, kw = mapf(lambda a, b='c': a, [], {})
    assert a == ('c',)
    assert kw == {}


def test_simple_no_name1():
    a, kw = mapf(lambda a, b='c': a, [('a', 3), (4, 'is_set')], {})
    assert a == (3, '4')
    assert kw == {}


def test_simple_no_name2():
    a, kw = mapf(lambda a=2, b='c': a, [('9', 'is_set'), (4, 'is_set')], {})
    assert a == (9, '4')
    assert kw == {}


def test_simple3_compl():
    with pytest.raises(Exception) as einfo:
        a, kw = mapf(
            lambda a, b=int: a,
            [],
            {'req_args_complete': True, 'allow_type_args': True},
        )
    assert einfo.value.args[0] == Exc.require_value
    assert einfo.value.args[1] == {'param': 'a'}


def test_simple3_compl_type():
    with pytest.raises(Exception) as einfo:
        a, kw = mapf(
            lambda a, b=int: a, [('a', 1)], {'req_args_complete': True}
        )
    assert einfo.value.args[0] == Exc.require_value
    assert einfo.value.args[1] == {'param': 'b', 'type': 'int'}


def test_simple4_compl_type():
    with pytest.raises(Exception) as einfo:
        a, kw = mapf(lambda a, b=int: a, [], {'req_args_complete': True})
    assert einfo.value.args[0] == Exc.require_value
    # the other one is only error logged.
    assert einfo.value.args[1] == {'param': 'b', 'type': 'int'}


def test_map_from():
    a, kw = mapf(lambda a, b, c='d': a, [('b', 1)], {}, map_from=1)
    assert a == (1, 'd')
    assert kw == {}


def test_map_from2():
    a, kw = mapf(lambda a, b, c='d': a, [('b', 1), ('c', 2)], {}, map_from=1)
    assert a == (1, '2')
    assert kw == {}


def test_positional():
    a, kw = mapf(lambda a, *b: a, [('a', 1)], {})
    assert a == (1,)
    assert kw == {}


def test_positional2():
    a, kw = mapf(lambda a, *b: None, [('a', 1), (2, 'is_set')], {})
    assert a == (1, 2)
    assert kw == {}


def test_positional3():
    a, kw = mapf(
        lambda a, *b: None, [('a', 1), (2, 'is_set'), ('3', 'is_set')], {}
    )
    assert a == (1, 2, '3')
    assert kw == {}


def test_positional_kw():
    a, kw = mapf(
        lambda a, A=1, *b, **kw: None,
        [('a', 1), (2, 'is_set'), ('3', 'is_set'), ('4', 'is_set')],
        {},
    )
    assert a == (1, 2, '3', '4')
    assert kw == {}


def test_positional_kw2():
    a, kw = mapf(
        lambda a, A=1, *b, **kw: None,
        [
            ('A', '42'),
            ('a', 1),
            (2, 'is_set'),
            ('3', 'is_set'),
            ('4', 'is_set'),
        ],
        {},
    )
    assert a == (1, 42, 2, '3', '4')
    assert kw == {}


def test_positional_kw3():
    a, kw = mapf(
        lambda a, A=1, *b, **kw: None,
        [
            ('A', '42'),
            ('a', 1),
            (2, 'is_set'),
            ('3', 'is_set'),
            ('4', 'is_set'),
            ('foo', 'bar'),
            ('bar', 'baz'),
        ],
        {},
    )
    assert a == (1, 42, 2, '3', '4')
    assert kw == {'bar': 'baz', 'foo': 'bar'}


def test_positional_mixed():
    a, kw = mapf(lambda a, A=42, *b, **kw: None, [('abc', 'is_set')], {})
    assert a == ('abc', 42)
    assert kw == {}


import sys

py3 = partial(
    pytest.mark.skipif,
    sys.version_info < (3, 0),
    reason='requires python3 or higher',
)


def f():
    # on py2 we could not compile this -> eval it on demand:
    return eval('lambda a, *b, c=1: None')


@py3()
def test_kw_positional3():
    a, kw = mapf(f(), [('a', 1), (2, 'is_set')], {})
    assert a == (1, 2)
    assert kw == {}


@py3()
def test_kw_positional4():
    a, kw = mapf(f(), [('a', 1), (2, 'is_set'), ('c', 2)], {})
    assert a == (1, 2)
    assert kw == {'c': 2}


@py3()
def test_kw_positional5():
    a, kw = mapf(f(), [('a', 1), (2, 'is_set'), (3, 'is_set'), ('c', 2)], {})
    assert a == (1, 2, 3)
    assert kw == {'c': 2}


# .
