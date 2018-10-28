from __future__ import absolute_import, print_function
from .common import nil, throw, Exc, is_str, PY2, breakpoint
from ast import literal_eval
from functools import partial
import attr

filepath = '<filepath>'

# --------------------------------------------------------- Casting From Strings

t_attr = type(attr.ib())


class plain_class:
    def __(self):
        pass


# for PY2:
_ = plain_class
t_funcs = (type(lambda x: x), type(_.__), type(partial(_.__)))
if PY2:

    class new_style_class(object):
        pass

    is_cls = lambda cls: type(cls) in (type(_), type(new_style_class))
else:
    is_cls = lambda cls: type(cls) == type(_)


def str_to_dict(cast, s, dflt):
    if s.startswith('{'):
        return literal_eval(s)
    try:
        return dict(
            [
                (k.strip(), v.strip())
                for k, v in [kv.split(':', 1) for kv in s.split(',')]
            ]
        )
    except:
        throw(Exc.cannot_cast_to_dict, val=s)


def str_to_list(cast, s, dflt):
    if s[0] in ['[', '(']:
        l = list(literal_eval(s))
    else:
        l = [i.strip() for i in s.split(',')]
    return l


def str_to_tuple(cast, s, dflt):
    if s[0] in ['[', '(']:
        l = literal_eval(s)
    else:
        l = [i.strip() for i in s.split(',')]
    return tuple(l)


false_strs = [
    '',
    '0',
    'false',
    'False',
    'nil',
    'None',
    'none',
    '{}',
    '[]',
    '()',
]


def str_to_bool(cast, s, dflt):
    if s in false_strs:
        return False
    if s[0].isdigit():
        try:
            return float(s)
        except:
            pass
    return s


attr_nothing = attr.ib()._default


def register_type_or_func(cast, type_or_func, name=None):
    n = name if name else funcname(type_or_func)
    f = getattr(cast, n, None)
    if f is None:
        # f = partial(type_or_func, cast)
        f = type_or_func
        setattr(cast, n, f)
    cast._all[type_or_func] = f
    cast._all[n] = f


@attr.s
class Cast(object):
    @classmethod
    def int(cast, s, dflt, ctx):
        return int(float(s))

    @classmethod
    def nearest_int(cast, s, dflt, ctx):
        return int(float(s) + 0.5)

    @classmethod
    def bool(cast, s, dflt, ctx):
        if isinstance(s, str):
            s = str_to_bool(cast, s, dflt)
        return bool(s)

    @classmethod
    def float(cast, s, dflt, ctx):
        return float(s)

    @classmethod
    def str(cast, s, dflt, ctx):
        return str(s)

    @classmethod
    def dict(cast, s, dflt, ctx):
        if isinstance(s, str):
            return str_to_dict(cast, s, dflt)
        d = dict(s) if not isinstance(s, dict) else s
        if not isinstance(dflt, dict) or not dflt:
            return d
        c = cast.__call__
        if len(dflt) == 1:
            # apply for all:
            K, V = tuple(dflt.items())[0]
            return dict([(c(k, K, ctx), c(v, V, ctx)) for k, v in d.items()])
        raise Exception(MultiKeyNotSupported)

    @classmethod
    def list(cast, s, dflt, ctx):
        if isinstance(s, str):
            l = str_to_list(cast, s, dflt)
        else:
            l = list(s) if not isinstance(s, list) else s
        return cast.deep_seq(l, dflt, list, ctx)

    @classmethod
    def tuple(cast, s, dflt, ctx):
        if isinstance(s, str):
            l = str_to_tuple(cast, s, dflt)

        else:
            l = tuple(s) if not isinstance(s, tuple) else s

        return tuple(cast.deep_seq(l, dflt, tuple, ctx))

    @classmethod
    def deep_seq(cast, l, dflt, into, ctx):
        if not isinstance(dflt, into) or not dflt:
            return l
        if len(dflt) == 1:
            return [
                cast.__call__(l[i], dflt[0], ctx) for i in range(0, len(l))
            ]

        return [cast.__call__(l[i], dflt[i], ctx) for i in range(0, len(l))]

    _all = None

    @classmethod
    def __call__(cast, s, dflt, ctx=None):
        """ public api: cast('3', int)"""
        into_type = dflt
        try:
            caster = cast._all.get(dflt)  # {} unhashable
        except:
            caster = None
        if not caster:
            if not callable(into_type):
                into_type = type(dflt)
            caster = cast._all.get(into_type)
            if not caster:
                if hasattr(into_type, '__code__'):
                    # adhoc caster:
                    return into_type(s, dflt=dflt, ctx=ctx)
                try:
                    mm = into_type.mro()
                except Exception as ex:
                    print('breakpoint set')
                    breakpoint()
                    keep_ctx = True
                for m in into_type.mro():
                    caster = cast._all.get(m)
                    if caster:
                        break
        if caster:
            try:
                return caster(s, dflt, ctx)
            except Exception as ex:
                kw = {'expected_type': try_find_name(caster, cast)}
                if ctx:
                    for k in ('for_param',):
                        v = ctx.get(k)
                        if v:
                            kw[k] = v
                kw['got'] = s
                throw(Exc.cannot_cast, **kw)
        if not caster:
            breakpoint()

    @classmethod
    def get(cast, caster):
        return cast._all.get(caster)

    @classmethod
    def add_caster(cast, caster, name=None):
        if cast._all is None:
            cast._all = {}
        register_type_or_func(cast, caster, name)


def try_find_name(caster, cast):
    try:
        a = cast._all.items()
        l = [(k, v) for k, v in a if v == caster and is_str(k)]
        if l:
            return l[0][0]
        raise
    except:
        return funcname(caster)


def funcname(f):
    n = getattr(f, '__name__', None)
    while not n:
        f = f.__func__
        n = getattr(f, '__name__', None)
    return n


cast = Cast()

for c in [cast.nearest_int, int, bool, float, str, dict, list, tuple]:
    try:
        cast.add_caster(c)
    except Exception as ex:
        print('breakpoint set')
        breakpoint()
        keep_ctx = True

if PY2:

    def new_style(cls):
        return (
            cls
            if is_new(cls)
            else type(cls.__name__, (cls, object), vars(cls))
        )

    is_old = lambda o, a=type(plain_class): type(o) == a
    is_new = lambda o, n=type(new_style_class): type(o) == n

    def recursive_to_new_style(cls, cast=cast):
        """
        recursive changing of inner classes to new style
        used in PY2 in def configure before doing anything.
        """
        for k in [s for s in dir(cls) if not s.startswith('_')]:
            v = getattr(cls, k)
            if v in cast._all:
                continue
            if is_new(v):
                recursive_to_new_style(v)
            if is_old(v):
                setattr(cls, k, recursive_to_new_style(v))
        return new_style(cls)

    def s(cls):
        return attr.orig_s(new_style(cls))

    attr.orig_s = attr.s
    attr.s = s

else:

    attrcls = attr.s
