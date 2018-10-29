
from __future__ import absolute_import, print_function
from .common import nil, PY2, breakpoint, throw, Exc, error

if PY2:
    from funcsigs import signature
else:
    from inspect import signature
from .casting import cast, is_cls

import time


def flatten_dotted_arg_from_dict(d, pth=None):
    while isinstance(d, dict):
        if not len(d) == 1:
            return
        k = list(d.keys())[0]
        pth = (k,) if not pth else pth + (k,)
        d = d.get(k)
        if d == 'is_set':
            return '.'.join(pth)


def fix_dotted_cli_vals(cli):
    """arguments can be given positionally, i.e. without keyname
    e.g. just appname foo.bar.baz. The CLI pre_parser puts this into
    {foo:{bar:{baz: is_set}}}
    We recreate into foo.bar.baz=is_set like other position vals here:
    """
    r = ()
    for K, d in cli:
        kv = flatten_dotted_arg_from_dict(d)
        if kv:
            K, d = '%s.%s' % (K, kv), 'is_set'
        r += ((K, d),)
    return r


def map_args_to_func_sig(
    f, cli, ctx, map_from=-1, prefer_positional=True, deep=True, cast=cast
):
    """
    inspect.signature based version.

    Py2: This WOULD work using the signature simulation for py2 (funcsigs)
    from https://funcsigs.readthedocs.io/en/0.4/
    but perf is lousy. See below, for 2 we do it in getargspec

    Maybe it can be done more effective, not sure yet:

    # update: We use funcsigs now for py2... maybe later add the argspec
    # version back again.

    """
    cli = fix_dotted_cli_vals(cli)
    if map_from == -1:
        # signature does not deliver cls or self, so no effort here:
        map_from = 0
    sig_dict = signature(f).parameters
    va_pos, have_va, pos_params = 0, False, []
    i = 0
    for n, p in sig_dict.items():
        i += 1
        if i <= map_from:
            continue
        if p.kind == p.VAR_POSITIONAL:
            have_va = True
            break
        va_pos += 1
        pos_params.append(n)

    args = [nil for i in pos_params]
    kw = {}

    def default(n):
        d = sig_dict.get(n)
        if not d:
            return nil
        return d.default if d.default != d.empty else nil

    idx, leng = -1, len(cli) - 1
    while idx < leng:
        idx += 1
        n, v = cli[idx]
        if v != 'is_set':
            d = default(n)
            if d != nil:
                v = cast(v, d, {'for_param': n})
            if have_va and n in pos_params:
                args[pos_params.index(n)] = v
                pos_params.remove(n)
            else:
                kw[n] = v
                pos_params.remove(n) if n in pos_params else None
        else:
            # v = is_set when no key is given, just value:
            if pos_params:
                vv = n  # the value
                n = pos_params.pop(0)  # the key
                d = default(n)
                v = cast(vv, d, {'for_param': n}) if d != nil else vv
            if have_va:
                app = True
                for i in range(0, len(args)):
                    if args[i] == nil:
                        args[i] = v
                        app = False
                        break
                if app:
                    args.append(n)
            else:
                kw[n] = v
    offset = args.index(nil) if nil in args else 0
    for n in list(pos_params):
        p = sig_dict[n]
        if p.default != p.empty and not is_cls(p):
            if have_va:
                args[pos_params.index(n) + offset] = p.default
                pos_params.remove(n)
            else:
                kw[n] = p.default
                pos_params.remove(n)

    argt = ()
    for a in args:
        if a != nil:
            argt += (a,)

    allow_types = ctx.get('allow_type_args', False)
    if ctx.get('req_args_complete'):

        ps, err = [], Exc.require_value
        for p in pos_params:
            d = default(p)
            if default(p) == nil:
                ps.append({'param': p})
            if not allow_types and type(d) == type:
                ps.append({'param': p, 'type': d.__name__})
        if not allow_types:
            for k, v in kw.items():
                if type(v) == type:
                    ps.append({'param': k, 'type': v.__name__})
        if ps:
            [error(err, **p) for p in ps[:-1]]
            throw(err, **ps[-1])

    if prefer_positional:
        for p in list(sig_dict.keys())[map_from:]:
            v = sig_dict[p]
            if v.kind != v.POSITIONAL_OR_KEYWORD:
                break
            vm = kw.pop(p, nil)
            if vm != nil:
                argt += (vm,)

    return argt, kw


def pretty_type(sigstr):
    return str(sigstr).replace('<class ', '<').replace('<type ', '<')


def repl_func_defaults(func, dflts, provider):
    orig = func.__defaults__
    pos = 0
    new = ()
    mod = {}
    old = {}
    for n, p in signature(func).parameters.items():
        if p.default == p.empty:
            continue
        od, newd = orig[pos], dflts.pop(n, nil)
        old[n] = od
        if newd != nil and newd != od:
            mod[n] = newd = cast(newd, od, {'for_param': n})
        else:
            newd = od
        new += (newd,)
        pos += 1

    if not PY2:
        # we mark what we did:
        # not writeable in py2:
        d = func.__doc__ or ''
        d += '\n:::warning\nDefaults modified (by %s):' % provider
        for k, v in mod.items():
            d += '\n- %s: %s (was %s)' % (k, v, pretty_type(old[k]))
        d += '\n:::\n'
        func.__doc__ = d
        func.__defaults__ = new
    else:
        func.__func__.__defaults__ = new
