import pytest
import sys
import time
from appdirs import user_config_dir
import os
import attr
import tempfile
import json
from functools import partial

dn = os.path.dirname
import devapps

# sys.path.insert(0, dn(dn(os.path.abspath(__file__))))
# import setup_method as devapps

# default providers:
CLI, Env, File = devapps.CLI, devapps.Env, devapps.File

Exc = devapps.Exc

log = []

root = devapps.root
parent = devapps.parent

inner = devapps.inner


def storelog(_, __, ev, store=log):
    store.append(dict(ev))
    return ev


from devapps.common import set_log, breakpoint

logger = set_log()
logger._processors.insert(2, storelog)

configure = partial(devapps.configure, log=logger)


fn_test = tempfile.mkstemp()[1] + '.test_mdv'


def clear(l):
    # py2 compat:
    while l:
        l.pop()


def write_file(d, fn=fn_test):
    with open(fn, 'w') as fd:
        fd.write(json.dumps(d))


def test_to_shorts():
    ctx = {}
    res = ctx['shorts'] = devapps.to_shorts(['foo', 'foo_e'])
    res.pop('_orig_shorts_', 0)
    assert res == {'f': 'foo', 'fe': 'foo_e', 'foo': 'foo', 'foo_e': 'foo_e'}
    with pytest.raises(Exception) as einfo:
        res = devapps.short_to_long(0, {'fo': 1}, 0, ctx)
    assert log[-1]['event'] == Exc.non_unique

    res = devapps.short_to_long(0, {'foo': 1}, 0, ctx)
    res.pop('_orig_shorts_', 0)
    assert res == {'foo': 1}
    res = devapps.short_to_long(0, {'f': 1}, 0, ctx)
    res.pop('_orig_shorts_', 0)
    assert res == {'foo': 1}
    res = devapps.short_to_long(0, {'foo_': 1}, 0, ctx)
    res.pop('_orig_shorts_', 0)
    assert res == {'foo_e': 1}


userdir = lambda fn: os.path.join(user_config_dir(), fn)


class TestFile(object):
    def test_file_provider_none(self):
        f = devapps.File(None)
        assert f.filename == None

    def test_file_non_exists(self):
        fn = 'xxxxxf%s' % time.time()
        with pytest.raises(Exception) as einfo:
            f = devapps.File(fn)
        assert einfo.value.args[0] == Exc.file_not_found
        assert einfo.value.args[1]['fn'] == userdir(fn)

    def test_file_from_App(self):
        """No Error if config file not present"""

        class FooApp:
            pass

        f = devapps.File(FooApp)
        assert f.filename == userdir('FooApp.json')
        with pytest.raises(Exception) as einfo:
            f = devapps.File(FooApp, ignore_missing=False)
        assert einfo.value.args[0] == Exc.file_not_found


class TestCliPreParser(object):
    def setup_method(self):
        self.c = CLI.pre_parse_cli

    def test_nested(self):
        """the preparser just builds a deep dict, no knowledge of anything else"""
        m = {}
        res = self.c('foo=b=ar -cd baz -d a.b.c=d i=1 f=1.1 a.B=false'.split())
        assert res == {
            '-cd': 'baz',
            '-d': 'is_set',
            'a': {'B': 'false', 'b': {'c': 'd'}},
            'f': '1.1',
            'foo': 'b=ar',
            'i': '1',
        }

    def test_switches(self):
        argv = ['foo=bar', '-c', 'fn', 'x', '-C']
        sw = {'-c': 'config_file', '-C': 'Cfg'}
        res = devapps.CLI(argv, sw)
        assert res.argvd == {
            'Cfg': 'is_set',
            'config_file': 'fn',
            'foo': 'bar',
            'x': 'is_set',
        }

        with pytest.raises(Exception) as einfo:
            argv.append('-d')
            devapps.CLI(argv, sw)
        assert log[-1]['event'] == Exc.not_a_switch
        assert '-d' in str(log[-1])

    def test_switches2(self):
        argv = ['foo=bar', 'a', 'b']
        res = devapps.CLI(argv).argvd
        assert res == {'a': 'is_set', 'b': 'is_set', 'foo': 'bar'}


class TestConfigure(object):
    def teardown_method(self):
        os.unlink(fn_test) if os.path.exists(fn_test) else 0

    def setup_method(self):
        ld = """
        some very loooooooooooooooooooong long
        description
        """

        class Inner:
            b_i_dflt = True
            s_i_dflt = 'inner_str'

            def do_inner(self, argument, foo=int):
                return {'inner.do_inner': root(self).do_func1((argument, foo))}

            class deep:
                b_d_dflt = True
                s_d_dflt = 'deep_str'
                f_d_float = attr.ib(
                    1.0, metadata={'long_descr': ld, 'descr': 'descr'}
                )

                def do_deep(self, argument, foo1=44):
                    """
                    Does deep stuff
                    """

                    return {
                        'deep_deep': (
                            argument,
                            foo1,
                            {
                                'root config': (
                                    root(self).b_no_dflt,
                                    root(self).i_no_dflt,
                                    root(self).i_dflt,
                                )
                            },
                            parent(self).do_inner((argument, foo1)),
                        )
                    }

                def do_deep_func1(cls, foo, bar=float, baz=bool):
                    """does deep func1 business"""
                    # func1
                    return {
                        'deep_func1': (foo, bar, baz, cls.do_deep(foo * 2))
                    }

        class MyApp:

            # fmt: off
            attr_inst    = attr.ib(1.1, converter=lambda x: x+x)
            b_no_dflt    = attr.ib(type=bool, metadata={'descr': 'a bool', 'long_descr': ld})
            b_dflt_True  = True
            b_dflt_False = False
            s_no_dflt    = str
            s_dflt       = 'foo'
            i_no_dflt    = int
            i_dflt       = 42
            f_no_dflt    = float
            f_dflt       = 42.0
            d_no_dflt    = dict
            l_no_dflt    = list

            inner        = Inner
            # fmt: on

            def do_run(cls, func_param):
                """return the complete setup of the app as one string"""
                cls = attr.asdict(cls)
                return dict(locals())

            def another_func(cls, foo):
                return cls.f_dflt

            def do_func1(cls, foo, bar1=float, baz=bool, *args, **kw):
                """does foo"""
                d = dict(locals())
                d.pop('cls')
                assert cls.another_func('foo') == cls.f_dflt
                return {'app.do_func1': d}

        # for -h tests:
        MyApp.__doc__ = """
            Test App

            Does stuff
            """

        # test perf:
        # s = 'bb_a'
        # for i in range(1, 1000):
        #    s += '_a'
        #    setattr(MyApp, s, i)
        #    setattr(MyApp.inner, s, i)
        self.App = MyApp
        self.configure = partial(configure, MyApp)
        clear(log)

    def test_ok(self, get_argv=False):
        argv = 'lnd=1,dnd=a:b:2,bnd=True,snd=sndfoo,ind=23,fnd=2.3'
        argv += ',i.bid=0,i.sid=inner_cust_str'
        argv += ',i.d.bdd=0,i.d.sdd=my_deep_str'
        argv += ',ai=1.2'
        argv = argv.split(',')
        if get_argv:
            return argv
        res = self.configure(CLI(argv, set_runner_func=False))[0]().do_run(
            'myp'
        )
        assert res == {
            'cls': {
                'attr_inst': 2.4,
                'b_dflt_False': False,
                'b_dflt_True': True,
                'b_no_dflt': True,
                'd_no_dflt': {'a': 'b:2'},
                'f_dflt': 42.0,
                'f_no_dflt': 2.3,
                'i_dflt': 42,
                'i_no_dflt': 23,
                'inner': {
                    'b_i_dflt': False,
                    'deep': {
                        'f_d_float': 1.0,
                        'b_d_dflt': False,
                        's_d_dflt': 'my_deep_str',
                    },
                    's_i_dflt': 'inner_cust_str',
                },
                'l_no_dflt': ['1'],
                's_dflt': 'foo',
                's_no_dflt': 'sndfoo',
            },
            'func_param': 'myp',
        }

    def test_dict_wrong_fmt(self):
        argv = 'lnd=1,b_no_dflt=True,d_no_dflt=2222223'.split(',')
        with pytest.raises(Exception) as einfo:
            res = self.configure(CLI(argv))
        assert log[-1]['event'] == Exc.cannot_cast_to_dict
        assert '2222223' in str(log[-1])

    def test_dict_lit_eval(self):
        sargv = (
            'lnd=1,b_no_dflt=True,d_no_dflt={"a": "b"},f_no_dflt=1,ind=1,snd=a'
        )
        argv = sargv.split(',')
        # with pytest.raises(Exception) as einfo:
        res = self.configure(CLI(argv))
        print(res[0]())
        assert attr.asdict(res[0]()) == {
            'attr_inst': 2.2,
            'b_dflt_False': False,
            'b_dflt_True': True,
            'b_no_dflt': True,
            'd_no_dflt': {'a': 'b'},
            'f_dflt': 42.0,
            'f_no_dflt': 1.0,
            'i_dflt': 42,
            'i_no_dflt': 1,
            'inner': {
                'b_i_dflt': True,
                'deep': {
                    'b_d_dflt': True,
                    'f_d_float': 1.0,
                    's_d_dflt': 'deep_str',
                },
                's_i_dflt': 'inner_str',
            },
            'l_no_dflt': ['1'],
            's_dflt': 'foo',
            's_no_dflt': 'a',
        }

    def test_sh_help(self):
        sargv = 'b_dflt_False=True,b_no_dflt=True,d_no_dflt={"a": "b"}'
        sargv += ',f_no_dflt=1,ind=1,snd=a,-hh'
        # with pytest.raises(Exception) as einfo:
        # with self.assertRaises(SystemExit):
        app, func = self.configure(CLI(sargv.split(',')))[:2]
        res = func(app())
        print(res)
        assert '# MyApp\n' in res
        assert '# deep_func1\n' in res
        assert 'ooooong' in res

    def ok_with_env(self, pref='', e=os.environ):
        argv = self.test_ok(get_argv=True)
        m = {}
        m[pref + 'MyApp_b_dflt_True'] = '0'
        m[pref + 'MyApp_inner_deep_f_d_float'] = '1.2'
        m[pref + 'MyApp_inner_deep_s_d_dflt'] = 'not_taken_is_in_cli_args'
        e.update(m)
        exp = {
            'cls': {
                'attr_inst': 2.4,
                'b_dflt_False': False,
                'b_dflt_True': False,
                'b_no_dflt': True,
                'd_no_dflt': {'a': 'b:2'},
                'f_dflt': 42.0,
                'f_no_dflt': 2.3,
                'i_dflt': 42,
                'i_no_dflt': 23,
                'inner': {
                    'b_i_dflt': False,
                    'deep': {
                        'b_d_dflt': False,
                        'f_d_float': 1.2,
                        's_d_dflt': 'my_deep_str',
                    },
                    's_i_dflt': 'inner_cust_str',
                },
                'l_no_dflt': ['1'],
                's_dflt': 'foo',
                's_no_dflt': 'sndfoo',
            },
            'func_param': 'myenvp',
        }
        env = 'MyApp' if not pref else pref + 'MyApp'
        res = self.configure((CLI(argv, set_runner_func=False), Env(env)))[
            0
        ]().do_run('myenvp')
        assert res == exp
        for k in m:
            del os.environ[k]

    def test_ok_with_env(self):
        self.ok_with_env()

    def test_ok_with_env_cust_prefix(self):
        self.ok_with_env(pref='foo')

    def test_unmatched_outer(self):
        # fmt:off
        class App:
            foo_bar_baz = 1
            class Inner: abd = 'd'
        # fmt:on
        with pytest.raises(Exception) as einfo:
            configure(
                App, CLI(['fbb=2', 'out_unmatched'], set_runner_func=False)
            )
        assert log[-1]['event'] == Exc.unmatched
        assert 'out_unmatched' in str(log[-1])

    def test_unmatched_inner(self):
        # fmt:off
        class App:
            foo_bar_baz = 1
            class Inner: abd = 'd'
        # fmt:on

        with pytest.raises(Exception) as einfo:
            configure(App, CLI(['fbb=2', 'I.inner_unmatched=4']))
        assert log[-1]['event'] == Exc.unmatched
        assert 'inner_unmatched' in str(log[-1])

    def test_insufficient(self):
        with pytest.raises(Exception) as einfo:
            self.configure(CLI(['bnd=0'], set_runner_func=False))
        l = log[-1]
        assert l['event'] == Exc.require_value
        assert 'no_dflt' in str(l)

    def test_short_collision(self):
        class App:
            foo_bar_baz = 1
            foo_baz_baz = 2

        with pytest.raises(Exception) as einfo:
            # needs an argument, otherwise the cli is not even checked for
            # short collisions:
            configure(App, CLI(['x'], set_runner_func=False))
        assert log[-1]['event'] == Exc.cannot_build_unique_short_form

    def test_file_struct(self):
        class App:
            foo = 1

            class Inner:
                ifoo = 2

        write_file({'foo': 2, 'Inner': {'ifoo': 3}})
        app = configure(App, File(fn_test))[0]
        app = app()
        assert app.foo == 2
        assert app.Inner.ifoo == 3

    def test_file_preset_function_params(self):
        """
        This is a bit of a crazy feature:

        We mutate the defaults(!) of functions in the tree according to
        what is given in the config file:
        """

        argv = self.test_ok(get_argv=True)
        # argv = [
        #    'lnd=1',
        #    'dnd=a:b:2',
        #    'bnd=True',
        #    'snd=sndfoo',
        #    'ind=23',
        #    'fnd=2.3',
        #    'i.bid=0',
        #    'i.sid=inner_cust_str',
        #    'i.d.bdd=0',
        #    'i.d.sdd=my_deep_str',
        #    'ai=1.2',
        # ]
        write_file(
            {
                'foo': 2,  # non existent, no error for File
                'i_no_dflt': 100,  # overwritten by cli
                'i_dflt': 101,  # not overwritten by cli
                'func1': {'bar1': 123.2, 'baz': True},
                'inner': {
                    'ifoo': 3,
                    'inner': {'foo': 42},
                    'deep': {
                        'b_d_dflt': False,
                        'deep': {'foo1': 43},
                        'deep_func1': {'bar': 1.2, 'baz': False},
                    },
                },
            }
        )
        app = self.configure([CLI(argv), File(fn_test)])[0]
        app = app()
        # if we do only app.inner.deep then deep (and app)
        # would not have the ._root set, so parent() and root() calls would not
        # work:
        deep = inner(app, 'inner', 'deep')
        res = deep.do_deep_func1(foo='myfoo')
        # check the functions called to understand the result.
        # Note: their defaults have been changed in the configure run!
        assert res == {
            'deep_func1': (
                'myfoo',
                1.2,
                False,
                {
                    'deep_deep': (
                        'myfoomyfoo',
                        43,
                        {'root config': (True, 23, 101)},
                        {
                            'inner.do_inner': {
                                'app.do_func1': {
                                    'args': (),
                                    'bar1': 123.2,
                                    'baz': True,
                                    'foo': (('myfoomyfoo', 43), 42),
                                    'kw': {},
                                }
                            }
                        },
                    )
                },
            )
        }
        self.setup_method()
        argv.append('-hhc')
        app, func = self.configure([CLI(argv), File(fn_test)])[:2]
        res = func(app())
        print(res)
        assert '```python' in res
        assert 'def do_deep_func1' in res
        assert 'return {' in res
        assert '### Actions\n' in res

        # 'deep': {'b_d_dflt': False, 'deep_func1': {'bar': 1.2}},

    def test_file_struct_and_cli(self):
        class App:
            foo = 1

            def do_run(cls):
                return 1

            class Inner:
                ifoo = 2

        write_file({'foo': 2, 'Inner': {'ifoo': 3}})
        app, func = configure(App, (CLI(['foo=5']), File(fn_test)))[:2]
        assert app().foo == 5
        assert app().Inner.ifoo == 3
        assert func(app()) == 1


class TestConfigureRunner(object):
    def setup_method(self):
        class App:
            foo = 1

            class Inner:
                ifoo = 2

                class Deep:
                    deep_attr = bool

                    def do_something(deep, arg1, i=int, float2=1.2):
                        return (
                            arg1,
                            float2,
                            i,
                            parent(deep).ifoo,
                            root(deep).foo,
                        )

        self.App = App

    def test_no_runner(self):
        with pytest.raises(Exception) as einfo:
            configure(self.App, CLI('foo=5,I.D.da=1,arg1=sth'.split(',')))
        assert log[-1]['event'] == Exc.cannot_determine_function

    def test_runner(self):
        app, func = configure(
            self.App, CLI('foo=5,I.D.da=1,I.D.s,arg1=sth,i=3'.split(','))
        )[:2]
        res = func(app())
        assert res == ('sth', 1.2, 3, 2, 5)
