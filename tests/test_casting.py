import pytest
from devapps.casting import cast
from devapps.common import Exc


def func():
    pass


class Test_bool(object):
    def test_true(self, caster=bool):
        truths = '[0]', '1', 1, 'true', 'True', True, '[0]', '(0)', '{"a" 1}'
        truths += (int, float, str, dict, list, tuple)
        truths += (func,)

        for t in truths:
            print(t)
            assert cast(t, caster) == True

    def test_false(self, caster=bool):
        for t in [
            '0',
            '0.000',
            'false',
            'False',
            'nil',
            'None',
            'none',
            '{}',
            '[]',
            '()',
        ]:
            print(t)
            assert cast(t, caster) == False


class Test_int(object):
    def test_accepted(self, caster=int):
        ints = (42, 42.9, 42.4, '42', '42.5', '42.9')
        for i in ints:
            print(i)
            assert cast(i, caster) == 42
        ints = (-42, -42.9, -42.4, '-42', '-42.5', '-42.9')
        for i in ints:
            print(i)
            assert cast(i, caster) == -42

    def test_int_fail(self, caster=int):
        for t in ['a', int, {}, [], (), 'nil', None, 'none', func]:
            with pytest.raises(Exception) as einfo:
                cast(t, int)
            assert einfo.value.args[0] == Exc.cannot_cast

    def test_int_overloaded(self):
        class i(int):
            pass

        self.test_accepted(caster=i)
        self.test_int_fail(caster=i)


class Test_custom(object):
    def test_accepted(self):
        def my_custom_caster(s, dflt, ctx):
            s = int(s)
            return 43 if s == 42 else s

        cast.add_caster(my_custom_caster, name='no_answer')
        for f, t in ((42, 43), ('42', 43), (1, 1)):
            assert cast(f, my_custom_caster) == t
            assert cast(f, 'no_answer') == t

        with pytest.raises(Exception) as einfo:
            cast('foo', my_custom_caster)
        assert einfo.value.args[0] == Exc.cannot_cast
        assert 'no_answer' in str(einfo.value)


def test_str_or_func_lookup():
    # fmt: off
    assert cast(42.5    , cast.nearest_int ) == 43
    assert cast(42.5    , 'nearest_int'    ) == 43
    assert cast('42.5'  , cast.nearest_int ) == 43
    assert cast('42.5'  , 'nearest_int'    ) == 43
    assert cast('-42.5' , 'nearest_int'    ) == -42
    # fmt: on


def test_str():
    assert cast(1, '1') == '1'
    assert cast('a', 'a') == 'a'


def test_float():
    assert cast(1.1, 1.1) == 1.1
    assert cast('1.1', 1.1) == 1.1


def test_list():
    assert cast('a,b', []) == ['a', 'b']
    assert cast([], []) == []
    assert cast([0], [3, 3]) == [0]
    assert cast('a,  b ', []) == ['a', 'b']
    assert cast('a,b ,c', list) == ['a', 'b', 'c']


def test_tuple():
    assert cast([0], (3, 3)) == (0,)
    assert cast([], ()) == ()
    assert cast('a,b', ()) == ('a', 'b')
    assert cast('a,  b ', ()) == ('a', 'b')
    assert cast('a,b ,c', tuple) == ('a', 'b', 'c')


def test_dict():
    assert cast({}, {}) == {}
    assert cast('a:b', {}) == {'a': 'b'}
    assert cast('a : b ', {}) == {'a': 'b'}
    assert cast('a:b :c', {}) == {'a': 'b :c'}
    assert cast('{"a":{"b":"c"}}', {}) == {'a': {'b': 'c'}}
    assert cast('{"a": {"b":"c"}}', {}) == {'a': {'b': 'c'}}


def test_nested_typed():
    assert cast(['1'], [0]) == [1]
    assert cast('[1,2,4.6]', [int]) == [1, 2, 4]
    assert cast('[0]', [int]) == [0]
    assert cast('[0, 1, [1]]', [int, str, []]) == [0, '1', [1]]
    assert cast('[0, 1, ["1"]]', [int, str, []]) == [0, '1', ['1']]
    assert cast('[0, 1, ["1"]]', [int, str, [0]]) == [0, '1', [1]]
    assert cast(['a'], [str]) == ['a']
    for k in (['a'], '[a]'):
        with pytest.raises(Exception) as einfo:
            cast('a', [int])
        assert einfo.value.args[0] == Exc.cannot_cast

    assert cast([1, (1, 2)], [str, tuple((int, str))]) == ['1', (1, '2')]
    assert cast('[1, (1, 2)]', [str, tuple((int, str))]) == ['1', (1, '2')]
    assert cast('1, 1, 2', [str, int, str]) == ['1', 1, '2']
    assert cast([1, {'a': [1, 2, '3']}], [int, {str: [str, int, bool]}]) == [
        1,
        {'a': ['1', 2, True]},
    ]

    assert cast([1.9, {'a': [1, 2.2, '3']}], [1, {'a': [str, int, bool]}]) == [
        1,
        {'a': ['1', 2, True]},
    ]

    assert cast(
        [1.9, {'a': [1, 2.9, '3']}],
        ['nearest_int', {'a': [str, cast.nearest_int, bool]}],
    ) == [2, {'a': ['1', 3, True]}]


def test_crazy_type():
    # ok now lets get crazy:
    def custom_fooer(s, dflt, ctx):
        return ctx['bar'] + str(s) + 'baz'

    ctx = {'bar': 'fu'}
    cf = custom_fooer
    cast.add_caster(custom_fooer, 'fooer')
    assert cast({'a': 'b'}, {cf: cf}, ctx) == {'fuabaz': 'fubbaz'}
    assert cast(
        [1, {'a': {'bar': [1, 1.1, 42]}}, 3],
        [str, {cf: {cf: [cf, int, str]}}, bool],
        ctx,
    ) == ['1', {'fuabaz': {'fubarbaz': ['fu1baz', 1, '42']}}, True]

    # name reference supported, we are registered:
    assert cast('bar', 'fooer', ctx) == 'fubarbaz'

    assert cast('bar', custom_fooer, ctx) == 'fubarbaz'


def test_crazy_type_adhoc_func():
    def custom_fooer2(s, dflt, ctx):
        return ctx['bar'] + str(s) + 'baz'

    ctx = {'bar': 'fu'}
    cf = custom_fooer2
    # no register:
    # cast.add_caster(custom_fooer, 'fooer')
    assert cast({'a': 'b'}, {cf: cf}, ctx) == {'fuabaz': 'fubbaz'}
    assert cast(
        [1, {'a': {'bar': [1, 1.1, 42]}}, 3],
        [str, {cf: {cf: [cf, int, str]}}, bool],
        ctx,
    ) == ['1', {'fuabaz': {'fubarbaz': ['fu1baz', 1, '42']}}, True]

    assert cast('bar', custom_fooer2, ctx) == 'fubarbaz'


# .
