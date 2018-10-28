from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
import sys, time
import pdb

breakpoint = pdb.set_trace  # leave - imported all around, for py2 tests

nil = '\x01'  # marker
PY2 = sys.version_info[0] < 3

# just for debug console output:
def get_add(ctx):
    ctx['pos'] += 1
    return ctx['pos']


now = lambda: time.time()
t0 = now()
pdt = lambda t0=t0, ctx={'pos': 0}, *a: print(get_add(ctx), now() - t0, a)
is_str = lambda s: isinstance(s, basestring if PY2 else str)

if PY2:
    # adding the convenient PY3 getoutput to sp.
    # hope correct (in plane, offline):
    import subprocess as sp

    def _(*a, **kw):
        kw['stdout'] = sp.PIPE
        kw['stderr'] = sp.PIPE
        kw['shell'] = True
        out, err = sp.Popen(*a, **kw).communicate()
        if out.endswith('\n'):
            out = out[:-1]
        return out + err

    sp.getoutput = _

# pdt(t0)

# -------------------------------------------------------------- Error Handling
class Exc:
    # fmt: off
    cannot_cast                    = 'Cannot cast'
    cannot_cast_to_dict            = 'Cannot cast to dict'
    unmatched                      = 'Unmatched'
    non_unique                     = 'Non unique'
    file_not_found                 = 'File not found'
    cannot_determine_function      = 'Cannot determine function to run'
    cannot_build_unique_short_form = 'Cannot build unique short form'
    not_a_switch                   = 'Not a known switch'
    require_value                  = 'Value required'
    req_dict_to_setup_class        = 'Require dict to setup class'
    double_func_call               = 'TWO functions on CLI disallowed'
    cannot_load_module             = 'Cannot load module'
    app_class_not_found            = 'Application class not found'
    app_error                      = 'Application runtime error'
    # fmt: on


def throw(event, *a, **kw):
    if a:
        kw['args'] = a
    error(event, **kw)
    raise Exception(event, kw)


# --------------------------------------------------------------------- logging

# We do a lot of delayed evaluation to avoid the import and instantiation of
# structlog loggers if there is no logging at our intended level - which is
# often if we just wrap a simple app -> fast call times in total then.
def add_dt(_, __, ev, ts=time.time()):
    dt = time.time() - ts
    ev['timestamp'] = '{:06.5f}'.format(dt)
    return ev


class plain_logger:
    @classmethod
    def log(cls, msg, *a, **kw):
        try:
            txt = ' '.join(
                (
                    msg,
                    ' '.join([str(i).strip() for i in a]),
                    ' '.join(['%s=%s' % (k, v) for k, v in kw.items()]),
                )
            )
        except:
            breakpoint()

        sys.stderr.write(txt + '\n')

    info = debug = error = warn = log


CFG = {'logger': plain_logger, 'min_level': 10}


def logger(level_nr, a, kw):
    l = CFG['logger']
    if level_nr < CFG['min_level']:
        return
    if isinstance(l, tuple):
        CFG['logger'] = l = get_structlogger(level=l[0], cfg=l[1])
    # log method - cached by nr:
    lm = CFG.get(level_nr)
    if not lm:
        rev = dict([(v, k) for k, v in lev_name_to_nr.items()])
        lm = CFG[level_nr] = getattr(l, rev.get(level_nr, 'info'))
    lm(*a, **kw)


def get_lazy_log(level, cfg):
    nr = lev_name_to_nr[level] if is_str(level) else level
    if nr != CFG['min_level']:
        # reconfig
        CFG['logger'] = (nr, cfg)
    CFG['min_level'] = nr
    return (level, cfg)


lev_name_to_nr = {
    'debug': 10,
    'info': 20,
    'warn': 30,
    'error': 40,
    'exception': 41,
}
# fmt: off
debug = lambda *a, **kw: logger(10, a, kw)
info  = lambda *a, **kw: logger(20, a, kw)
warn  = lambda *a, **kw: logger(30, a, kw)
error = lambda *a, **kw: logger(40, a, kw)
exception = lambda *a, **kw: logger(41, a, kw)
# fmt: on


def set_log(log=None):
    if log is not None:
        l = CFG['logger'] = log
    else:
        l = CFG['logger'] = get_structlogger()
    return l


def filter_by_level(_, level, ev, cfg_level, level_nr, drop):
    if level_nr[level] < cfg_level:
        raise drop
    return ev


def fmt_msg(_, __, ev):
    # special treatment here for nice output:
    msg = ev.get('msg')
    if not msg or not isinstance(msg, tuple):
        return ev
    ev['msg'] = ' '.join([str(p) for p in msg])
    return ev


def get_structlogger(level=10, cfg=None):
    import structlog as sl  # we did a lot of crap to avoid that if no logging is done

    if cfg is None:
        cfg = {}

    ntl = sl.stdlib._NAME_TO_LEVEL
    level = ntl[level] if is_str(level) else level
    drop = sl.exceptions.DropEvent

    p = [
        partial(filter_by_level, cfg_level=level, level_nr=ntl, drop=drop),
        add_dt,
        sl.stdlib.add_log_level,
        fmt_msg,
    ]
    if level < 20:
        p.append(sl.processors.StackInfoRenderer())
    p.extend([sl.processors.format_exc_info, sl.dev.ConsoleRenderer(**cfg)])

    log = sl.wrap_logger(
        sl.PrintLogger(file=sys.stderr), processors=p, context_class=dict
    ).bind()
    return log
