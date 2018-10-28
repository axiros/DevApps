from __future__ import absolute_import, print_function
import sys, os, traceback
from .casting import attr, is_str, is_cls
from .help import render_help
from .common import (
    get_lazy_log,
    pdt,
    Exc,
    throw,
    debug,
    info,
    warn,
    error,
    exception,
)
from devapps import common, root, parent, as_dict
from devapps import configure, CLI, Env, File

breakpoint = common.breakpoint


def call_if_cls(ac, _, val):
    if is_str(ac.imp_name):
        return  # deco with args
    App = ac.imp_name
    if is_cls(App):
        # deco called w/o args
        ac.exit = True
        ac.imp_name = '__main__'
        set_logger(ac, 0, 'error')
        ac.__call__(App)
        # we are in validate of the first arg. can't return stuff


def log_cfg(ac):
    return dict(
        pad_event=10, colors=ac.colors != False, force_colors=ac.colors == True
    )


def set_logger(ac, attr, val):
    if ac.imp_name == '__main__':
        ac.logger = get_lazy_log('error', log_cfg(ac))


@attr.s
class app(object):
    """The App decorator"""

    # in the validator for the first argument we'll see if the decorator
    # was applied without arguments, i.e. this will be set to the decorated
    # class then - otherwise, with args, we require '__main__' to immediatelly
    # run the app:
    # fmt: off
    imp_name          = attr.ib(None,   type = str, validator = call_if_cls)

    fmt_res           = attr.ib('auto', type = str)
    colors            = attr.ib('auto', type = str)
    req_args_complete = attr.ib(False,  type = bool)
    log_call_errs     = attr.ib(True,  type = bool)
    exit              = attr.ib(default= False, type = bool)
    log_level         = attr.ib(default= 'error', type = str, validator = set_logger)
    cli_argv          = attr.ib(default=None, type=list)
    debug_mode        = attr.ib(default=0, type=int)
    # fmt: on

    log = None

    def format_result(ac, res):
        if ac.fmt_res is False:
            return res
        return res

    def colorize_result(ac, res):
        return res

    def __call__(ac, App):
        if not ac.imp_name == '__main__':
            return App

        if ac.exit:
            ac.req_args_complete = True
            ac.log_call_errs = True
        try:
            n = App.__name__
            if ac.cli_argv == None:
                ac.cli_argv = sys.argv[1:]

            app, func = configure(
                App,
                providers=(CLI(ac.cli_argv), Env(n), File(App)),
                req_args_complete=True,
                log_err=ac.log_call_errs,
                log=ac.logger,
            )[:2]

            res = func(app())
            # except ValueError as ex:
        except Exception as ex:
            # print('debug', ex)

            ac.log = get_lazy_log(ac.log_level, log_cfg(ac))
            if ac.log_level == 'debug':
                exception(Exc.app_error, exc_info=ex)
            if ac.log_level in ('info', 'debug'):
                info(Exc.app_error, err=str(ex))
            if ac.exit:
                sys.exit(1)
            raise
        print(res)
        res = ac.format_result(res)
        if ac.exit:
            res = ac.colorize_result(res)
        return res

    def do_run(ac, module_name=str, class_name=str, *app_args, **app_kw):
        """the method run when we are used via the entrymethod
        Our Job: Get a hold on the App class:

        Convenience:
        If use does not deliver the class_name we try search the ONE class
        in the module - the class_name parameter will then be treated as first
        argv of the app itself.
        """

        mod = None
        mn = module_name
        for i in range(2):
            try:
                mod = __import__(mn)
                break
            except:
                if mn.endswith('.py'):
                    mn = os.path.abspath(mn)
                    sys.path.insert(0, os.path.dirname(mn))
                    mn = mn.rsplit('/', 1)[1][:-3]
        if not mod:
            import imp

            (fd, pathname, description) = imp.find_module(mn)
            try:
                mod = imp.load_module(mn, fd, pathname, description)
            finally:
                fd.close()

        if not mod:
            throw(Exc.cannot_load_module, module_name=module_name)

        App, argv_offs = getattr(mod, str(class_name), None), 0
        if not App:
            # class_name is then first parameter of the App if we can determine
            # it (one class in the module):
            argv_offs = -1
            App = [
                getattr(mod, n) for n in dir(mod) if is_cls(getattr(mod, n))
            ]

            if len(App) > 1:
                throw(Exc.non_unique, classes=[A.__name__ for A in App])
            if len(App) == 1:
                App = App[0]

        if not App:
            throw(
                Exc.app_class_not_found,
                class_name=class_name,
                module_name=module_name,
            )
        if not ac.cli_argv:
            ac.cli_argv = sys.argv[
                sys.argv.index(module_name) + 2 + argv_offs :
            ]
        ac.imp_name = App
        res = call_if_cls(ac, '', App)
        return res

    def do_help(ac):
        h = render_help(ac, 'h', None)
        print(h)
        return h


def run():
    """Entrymethod in setup.py for devapps executable
    We first configure devapps itself, then configure the class, then run
    Example:
    devapps colors=false modulefilename classname foo=bar

    """

    class App(app):
        _cli_help_switch = '-\x01'
        # __attrs_attrs__ = None

    attrs = app.__attrs_attrs__
    for v in attrs:
        setattr(App, v.name, attr.ib(default=v.default, validator=v.validator))
    get_lazy_log('error', log_cfg(App))
    acapp, func = configure(App, req_args_complete=True)[:2]
    res = func(acapp())
