from __future__ import absolute_import, print_function
from .version import __version__

import time
import string
import sys
import os
import json

from ast import literal_eval
from appdirs import user_config_dir
from functools import partial


from .func_sigs import map_args_to_func_sig, repl_func_defaults
from .func_sigs import flatten_dotted_arg_from_dict
from .casting import funcname, cast, t_attr, t_funcs
from .casting import is_cls, attr


from devapps import common

nil = common.nil
Exc = common.Exc
throw = common.throw
is_str = common.is_str
breakpoint = common.breakpoint
from .common import set_log, info, debug, warn, error, get_structlogger

odict = dict
if common.PY2:
    from .casting import recursive_to_new_style
    from collections import OrderedDict

    # unfortuntatelly in py2 dicts are not insertion ordered.
    # we rely on this, .e.g in pre_parse_cli:
    odict = OrderedDict


# -------------------------------------------------------- Base Config Provider
class Provider(object):
    # fmt: off
    str_only             = False
    allow_short_keys     = False
    set_runner_func      = False
    allow_unknown_attrs  = True
    show_help            = None
    # fmt: on

    def get_inner(cli, d, path, attrs, cfg):
        return d.get(path[-1])


# -------------------------------------------------------------- Key Shortening


def shorten(k):
    """
    k an attrname like foo_bar_baz.
    We return fbb, fbbaz, which we'll match startswith style if exact match
    not unique.
    """
    parts = k.split('_')
    r = ''.join([s[0] for s in parts if s])
    return r, r + parts[-1][1:]


def to_shorts(longs, shorten=shorten):
    """build a dict of short forms pointing to their original forms

    Collisions: We'll complain for foo_bar_baz and foo_baz_baz attrs
    and don't try to be smart here. Thats why we need the 'have' list.
    """
    m = odict()
    have = set()
    for k in longs:
        m[k] = k  # allowed match stsarts with also ok
        sh, sh_ending = shorten(k)
        if sh in have:
            # thats ok, colliding shorts
            m.pop(sh)
        else:
            m[sh] = k
            have.add(sh)
            if sh == sh_ending:
                # thats ok:
                continue
        if sh_ending in have:
            # developer has to rename the attribute if he wants the feature
            throw(
                Exc.cannot_build_unique_short_form,
                key=k,
                colliding=sh_ending,
                have=have,
            )
        m[sh_ending] = k
        have.add(sh_ending)
    return m


def short_to_long(provider, d, attrs, ctx):
    shorts = ctx.get('shorts')
    if not shorts:
        shorts = ctx['shorts'] = to_shorts([l[0] for l in attrs if l])
    nd = odict()
    orig_shorts = {}
    for k in d:
        if k in ('', '/'):
            # a "key" started with a '.' or '/' -> MUST be a positional arg and not a
            # key:
            k = flatten_dotted_arg_from_dict(d[k])
            nd[k] = 'is_set'
            continue

        try:
            # nd[shorts[k]] = d[k]
            h = shorts[k]
        except:
            h = [p for p in shorts if p.startswith(k)]
            if len(h) > 1:
                throw(Exc.non_unique, key=k, have=h)
            if len(h) == 1:
                h = h[0]
                # nd[shorts[h[0]]] = d[k]
            else:
                h = k
        nd[h] = d[k]
        orig_shorts[h] = k
    nd['_orig_shorts_'] = orig_shorts
    return nd


# ------------------------------------------------------------------------- CLI


def cli_prov(App, argv=None):
    if argv is None:
        argv = sys.argv[1:]
    cli = CLI(argv, help_switch=getattr(App, '_cli_help_switch', '-h'))
    return cli


@attr.s
class CLI(Provider):
    # fmt: off
    argvd                  = attr.ib(type= odict, converter = lambda x: CLI.pre_parse_cli(x))
    switches               = attr.ib(default={}, validator = lambda *x: CLI.set_switches(*x))
    allow_short_keys       = attr.ib(True)
    set_runner_func        = attr.ib(True)
    bool_reverse_on_no_val = attr.ib(True)
    str_only               = attr.ib(True)
    allow_unknown_attrs    = attr.ib(False)
    help_switch            = attr.ib('-h')
    # fmt: on

    @staticmethod
    def pre_parse_cli(argv):
        """just take the command line appart, w/o knowledge of app vars yet
        What we do though is to build nested dicts for f.b=bar style vars
        """
        r, _into = odict(), CLI.into
        idx, leng = -1, len(argv) - 1
        while idx < leng:
            idx += 1
            arg = argv[idx]
            if '=' in arg:
                k, v = arg.split('=', 1)
                _into(r, k, v)
                continue
            if idx == leng:
                if arg.startswith('-') and len(arg) > 2:
                    # -hhhc -> hhhc
                    _into(r, arg[:2], arg[1:])
                else:
                    _into(r, arg, 'is_set')
            elif argv[idx + 1].startswith('-') or '=' in argv[idx + 1]:
                # next one starts with - or is a key=val assignment -> this one is
                # bool:
                _into(r, arg, 'is_set')
            elif arg.startswith('-'):
                # app -c foo
                idx += 1
                _into(r, arg, argv[idx])
            else:
                # app 1 2
                _into(r, arg, 'is_set')

        return r

    @staticmethod
    def into(m, k, v):
        l = k.split('.')
        if l[0] in ('', '/'):
            # is a positional arg:
            m[k] = 'is_set'
            return
        # just a float, not a path 1.23:
        if l[0].isdigit():
            m[k] = v
            return

        for p in l[:-1]:
            m = m.setdefault(p, {})
        m[l[-1]] = v

    @staticmethod
    def set_switches(cli, attr, switches):
        if not switches:
            return
        # must preserve the order of original, can't just replace:
        d = odict()
        for k, v in cli.argvd.items():
            if not k.startswith('-'):
                d[k] = v
            else:
                try:
                    d[switches[k]] = v
                except:
                    throw(Exc.not_a_switch, found=k, known=switches)
        cli.argvd = d

    # @staticmethod
    # def is_switch(_, __, s):
    #    ''' not in use '''
    #    if not s in string.ascii_letters:
    #        throw(Exc.not_a_switch, s)

    def cfg(cli):
        hs = cli.argvd.pop(cli.help_switch, None)
        if hs is not None:
            cli.show_help = hs
        return cli.argvd


# --------------------------------------------------------------------- Environ


def conv_str(v):
    if v and v[0] in ('[', '(', '{'):
        try:
            return literal_eval(v)
        except:
            return v
    return v


@attr.s
class Env(Provider):
    prefix = attr.ib(default='', type=str, converter=lambda p: (p + '_'))
    str_only = attr.ib(True)

    def build_env_dict(env):
        e = os.environ
        l = len(env.prefix)
        return odict(
            [(k[l:], conv_str(e[k])) for k in e if k.startswith(env.prefix)]
        )

    def cfg(env):
        return env.build_env_dict()

    def get_inner(env, d, path, attrs, cfg):
        p = path[-1] + '_'
        l = len(p)
        d = odict([(k[l:], v) for k, v in d.items() if k.startswith(p)])
        return d


# ------------------------------------------------------------------------ File


@attr.s
class File(Provider):
    filename = attr.ib(
        default='', type=str, validator=lambda self, attribs, v: self.load(v)
    )
    filetype = attr.ib(default='json')
    ignore_missing = attr.ib(default=None)
    _cfg = attr.ib(default={})

    def cfg(file):
        return file._cfg

    def load(file, fn):
        if not fn:
            return
        die = False
        if is_str(fn):
            die = True
        else:
            # app class given:
            fn = fn.__name__ + '.' + file.filetype
        if file.ignore_missing != None:
            die = not file.ignore_missing
        try:
            if not os.path.exists(fn):
                fn = os.path.join(user_config_dir(), fn)
            fn = os.path.abspath(fn)
            file.filename = fn
            with open(fn) as fd:
                s = fd.read()
            file._cfg = json.loads(s)
        except Exception as ex:
            msg = Exc.file_not_found
            args = odict(exc=ex, fn=fn)
            if die:
                throw(msg, **args)
            debug(msg, **args)


# --------------------------------------------------------- Programmed Defaults


@attr.s
class Defaults:
    cls = attr.ib()
    cfg = {}


have_func = '\x04'


def was_a_dotted_positional_arg(cfg_val, key, prov):
    """
    This handles a special case:
    class App:
        def do_run(app, some_arg_with_dotted_value): pass
    If the `some_arg_with_dotted_value` is given positionally (supported for
    func params), .e.g. foo.bar.baz then we'll CLI preparse it into:
    {foo: {'bar': 'is_set'}} - and foo might be even considered a do_foo func.
    """
    was = flatten_dotted_arg_from_dict(cfg_val)
    if not was:
        return
    was = '%s.%s' % (key, was)
    m = {}
    for k, v in prov[1].items():
        if k == key:
            k, v = was, 'is_set'
        m[k] = v
    prov[1] = m
    return True


def walk_attrs(cls, providers, ctx):
    """
    here we burn startup time - recursively scanning all(!) cls attrs of the app.
    have to see if we should cache the scan results.

    """
    path = cls._path

    # first we build all infos about the attrs within our class:
    # (value, type, isit a (do) function):
    def nfo(cls, k):
        v = getattr(cls, k)
        t = type(v)
        ft = t in t_funcs
        if ft:
            if not k.startswith('do_'):
                return
            k = k[3:]
        return k, v, t, ft

    attrs = [nfo(cls, k) for k in dir(cls) if not k.startswith('_')]

    # now get fetch config from all providers regrding this class nesting
    # level:
    if path:
        providers = list(
            filter(
                lambda p: p[1],
                [
                    [p, p.get_inner(cfg, path, attrs, ctx), str_only]
                    for p, cfg, str_only in providers
                ],
            )
        )
    else:
        # first level:
        h = [l for l in [p[0].show_help for p in providers] if l is not None]
        if h:
            ctx['show_help'] = h[0]
        ctx['funcs'] = {}
    sh_help = ctx.get('show_help')

    # now the shorts matching:
    ctx['shorts'] = None
    # if path == ('inner', 'deep'):
    #    breakpoint()
    providers = [
        p
        if not p[0].allow_short_keys
        else [p[0], short_to_long(p, p[1], attrs, ctx), p[1]]
        for p in providers
    ]

    func, have_attrs = None, set()

    # now the replacement run over all attrs - and the casting:
    # if the value is a nested class we recurse:
    for l in attrs:
        if not l:
            continue
        # key value, type, is function_type of the original class:
        k, v, t, ft = l
        v_orig = v

        have_attrs.add(k)
        # if k == 'b_dflt_False':
        #    breakpoint()
        have_cfg = False
        from_prov = None
        for p in providers:
            cfg_val = p[1].get(k, nil)
            if cfg_val != nil:
                have_cfg = True
                str_only = p[2]
                # e.g. CLI:
                from_prov = p[0].__class__.__name__
                break

        if t != type:
            # an instance. Like: some_bool=True
            # or a function type?
            if ft:
                if have_cfg:
                    if isinstance(cfg_val, dict):
                        _ = p[0].__class__.__name__
                        # uh-oh: A positionally given dotted arg collides with
                        # a do function name?
                        if was_a_dotted_positional_arg(cfg_val, k, p):
                            have_attrs.remove(k)
                            have_cfg = False
                            continue
                        repl_func_defaults(func=v, dflts=cfg_val, provider=_)
                    # (else we just have 'is_set' if its the function req. to
                    # run - then we do not change defaults)
                    if p[0].set_runner_func:
                        # might be nested in cli dict, i.e. earlier attrs still to come
                        func = [path, v]
                continue

            if t == t_attr:
                if have_cfg:
                    typ = v.type or type(v._default)
                    v._default = cast(cfg_val, typ) if str_only else cfg_val
                    # already an attr.ib:
            else:
                if have_cfg:
                    v = cast(cfg_val, t) if str_only else cfg_val
                v = attr.ib(v)
        else:
            # a typ - no value. E.g. some_bool = bool
            caster = cast.get(v)
            if caster:
                if not have_cfg:
                    if sh_help:
                        # values not required then:
                        cfg_val = v.__name__
                        caster = lambda s, v, ctx: 'req:<%s>' % s
                    else:
                        throw(Exc.require_value, key=k)
                v = attr.ib(caster(cfg_val, v, ctx) if str_only else cfg_val)
            else:
                v._path = path + (k,)
                v, inner_func = walk_attrs(v, providers, ctx)
                if inner_func and func:
                    throw(
                        Exc.double_func_call,
                        func1=funcname(func1),
                        func2=funcname(inner_func),
                    )
                if not func and inner_func:
                    func = inner_func

                # v = attr.ib(factory=lambda cls=v: cls())
                v = attr.ib(factory=lambda cls=v: cls())

        v.metadata['orig'] = v_orig
        v.metadata['provider'] = from_prov
        setattr(cls, k, v)

    for p in providers:
        # cli is a provider which sets the runner func:
        p[1].pop('_orig_shorts_', 0)
        if not path:
            # first level:
            h = ctx.get('show_help')
            if h is not None:
                return (attr.s(cls), ((), (show_help, (), {'level': h})))

            if p[0].set_runner_func:
                if not func:
                    dflt_func = getattr(cls, 'do_run', None)
                    if not dflt_func:
                        throw(Exc.cannot_determine_function)
                    func = [(), dflt_func]
                params = [
                    (k, v) for k, v in p[1].items() if not k in have_attrs
                ]
                path, func = func
                args = map_args_to_func_sig(func, params, map_from=1, ctx=ctx)
                return attr.s(cls), (path, (func,) + args)

        # now find unknown kvs at deeper levels:
        if not p[0].allow_unknown_attrs:
            unknown = [k for k in p[1] if not k in have_attrs]
            if unknown:
                throw(Exc.unmatched, unknown=unknown)

    return attr.s(cls), func


def show_help(app, level=None, h=None):
    from .help import render_help

    return render_help(app, level, h)


def inner(app, *pth):
    root = app
    app._root = app
    for p in pth:
        app = getattr(app, p)
    app._root = root
    return app


def err_log_wrapped(func, log, app):
    try:
        return func(app)(*a, **kw)
    except Exception as ex:
        msg = ex.args
        # we might check here if the app already logged (e.g. check last
        # msg)
        throw(ex.__class__.__name__, msg=msg)


def get_func(pth, func_with_args, log_err, log, app, *a, **kw):
    obj = inner(app, *pth)
    func, args, kwg = func_with_args
    args += a
    kwg.update(kw)
    return func(obj, *args, **kwg)


def root(obj):
    return obj._root


def parent(obj):
    r = root_ = root(obj)
    for p in obj._path[:-1]:
        r = getattr(r, p)
        r._root = root_
    return r


def as_dict(obj):
    return attr.asdict(obj)


def configure(
    App, providers=None, req_args_complete=False, log_err=False, log=None
):
    if common.PY2:
        recursive_to_new_style(App)

    set_log(log)
    if not providers:
        # take reasonable defaults
        n = App.__name__
        providers = (cli_prov(App), Env(n), File(App))
    if not isinstance(providers, (tuple, list)):
        providers = [providers]
    App._path = ()
    ctx = {}
    ctx['req_args_complete'] = req_args_complete
    App, pth_func_with_args = walk_attrs(
        App, [[p, p.cfg(), p.str_only] for p in providers], ctx
    )
    # pdt(t0)
    if pth_func_with_args:
        pth, func_with_args = pth_func_with_args
        func = partial(get_func, pth, func_with_args, log_err, log)
    else:
        func = None
    return App, func
