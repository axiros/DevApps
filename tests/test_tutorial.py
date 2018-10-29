"""
Creates The Tutorial - while testing its functions.

"""

import subprocess as sp
import pytest
import devapps
import os
import appdirs
import time
from ast import literal_eval as ev

breakpoint = devapps.common.breakpoint


class TestChapter1:
    def test_one(self):
        t = """

        [TOC]

        # `devapp`: Command Line Function Configurator and Runner

        Given you have a setup like this:

        <from-file: calc.py>

        Via the `devapp` command, you can provide config on the CLI (in addition to
        config file and environ) and run this right away:

        """
        md(t)
        ac, d_ac = appcond_cmd()
        ac = ac + ' ' + dtut + 'calc.py '
        res = bash_run(
            [
                ac + '41 1',
                ac + 'b=1 41',
                ac + 'oper_func=mul a=2 b=100',
                ac + 'of=mul a=2 b=150',
                """export Calc_oper_func=mul Calc_run='{"a":100}'; %s b=4"""
                % ac,
                ac + 'a=1 b=foo # b has wrong type',
                ac + '# missing params',
                ac + 'of=mul -h # help output',
            ],
            no_cmd_path=True,
            no_show_in_cmd=d_ac + '/',
        )
        for i, j in ((0, 42), (1, 42), (2, 200), (3, 300), (4, 400)):
            assert res[i]['res'].strip() == str(j)
        assert Exc.cannot_cast in res[5]['res']
        assert Exc.require_value in res[6]['res']
        assert 'oper_func' in res[7]['res']
        assert '# ' in res[7]['res']

        t = """

        # `@app`: Converts Class Trees

        The decorator variant allows to run the application standalone:

        <from-file: calc1.py>

        We
        - added a hashbang and made the file executable.
        - decorated the toplevel class.

        We can run the thing now from the CLI, directly:


        """
        md(t)
        res = bash_run(
            [
                'calc1.py a=2 b=4',
                'calc1.py b=2 a=4 # mappable so supported',
                'calc1.py 2 4.1 # positionally given, rounded',
                'calc1.py a=2 4.1 # mapping found',
                'calc1.py oper_func=mul a=2 b=4',
                'calc1.py of=mul a=2 b=4 # short form for oper_func',
            ]
        )
        assert res[0]['res'] == '6'
        assert res[1]['res'] == '6'
        assert res[2]['res'] == '6'
        assert res[3]['res'] == '6'
        assert res[4]['res'] == '8'
        assert res[5]['res'] == '8'

    def test_actions(self):
        t = """
        ## More Actions

        A class may have more action functions (by default prefixed with `do_`.
        `do_run` was just the default action - run if no other is configured.

        Lets add another one:

        <from-file: calc2.py>

        and run it:
        """
        md(t)
        res = bash_run(
            [
                'calc2.py list_sum "1,2,3"',
                'calc2.py ls "1, 2, 3" # short form for function supported',
            ]
        )
        assert res[0]['res'] == '6'
        assert res[1]['res'] == '6'

    def test_help(self):
        t = """
        ## Help Output

        `-h` delivers a markdown formatted help output:
        """
        md(t)
        res = bash_run(['calc2.py -h'], res_as=markdown)
        assert '## Actions' in res[0]['res']
        assert '```python' not in res[0]['res']
        t = """
        ### Markdown?

        Because this allows to add a lot of structuring information - which we can use to nicely colorize the output, provide TOCs, put into README's and so on.

        """
        md(t)

        md('`-hc` shows the implementation:')
        res = bash_run(['calc2.py -hc'], res_as=markdown)
        assert '``python' in res[0]['res']
        md(
            """
        > If the terminal width is not wide enough for the parameter tables we render the parameters vertically.
        > `-hu` (classic unix) forces this always.
        """
        )

        md(
            """
        ### Defaults Are Configurable
        Lets check `-h` output when arguments are supplied:
        """
        )
        res = bash_run(
            ['calc2.py of=multiply 1 -h | head -n 10'], res_as=markdown
        )
        assert 'multiply' in res[0]['res']
        md(
            """
        As you can see our value from the CLI made it into the documentation.  
        The `F` (From) column shows where the value was comming from.
        """
        )

    def test_file_providers(self):
        ''
        tt = """
        # Providers

        Changing the defaults of an app makes more sense to do via other means
        than the CLI.

        Built in we do have two more so called "providers", i.e. deliverers of config:

        `0.` [Programmed Defaults]
        `1.` Config File
        `2.` Environ
        `3.` CLI

        overriding each other's values in the given order. That order can be changed.

        ## File

        Lets create a config file, changing the default operator to `mul` and also the default of the first *function parameter* `a`:

        """
        md(tt)
        val = '10.3'
        res = bash_run(
            """python -c "if 1:
        cfg = {'oper_func': 'mul', 'run': {'a': %s}}

        # write to user config dir:
        from appdirs import user_config_dir as ucd
        from json import dumps
        with open(ucd() + '/Calc.json', 'w') as fd:
            fd.write(dumps(cfg))"
            """
            % val,
            no_cmd_path=True,
        )
        md(
            'Now we can run the app *without* supplying `a` and get a multiplication:'
        )
        res = bash_run(['calc1.py b=42'])
        assert res[0]['res'] == '420'
        md(
            """> Positionally you could overwrite `a` still on the CLI, so we do not map one value only to `b`"""
        )

        res = bash_run(['calc1.py 5 42'])
        assert res[0]['res'] == '210'
        res = bash_run(['calc1.py 5'])
        md('Here is the output of `-h`:')

        res = bash_run(['calc1.py -h'], res_as=markdown)
        assert 'mul' in res[0]['res']
        assert not val in res[0]['res']

        md('Again the app was reconfigured - this time by the config file (F)')
        md(
            """
        Observe the int value - it was converted from the float, since that is what the function explicitly asked for.
        """
        )
        md(
            '> Yes, we did mutate inplace the defaults of the `Calc.do_run` function - i.e. process wide!'
        )
        md(
            '> Keep this in mind when using that feature - reading the source code is then misleading.\n'
            '> Help output shows modifications and origin rather prominently as you can see.\n\n'
        )

        md('We delete the file for now.')

        del_user_calc_json()

    def test_env_providers(self):
        t = """
        ## Environ

        Supported as well - but you have to provide structed values in lit.eval form:"""
        md(t)
        res = bash_run(
            """export Calc_oper_func=mul Calc_run='{"a":4.2}'; %s/calc1.py b=3"""
            % dtut,
            no_cmd_path=True,
        )
        assert res[0]['res'] == '12'
        md(
            """
            > By default we do NOT support short forms at the environ provider and also we are case sensitive.
            > Note that the overridden defaults still had been casted to the original types of the function signature.
            """
        )
        md('\n\nHelp output, as expected:')

        res = bash_run(
            """export Calc_oper_func=xxx Calc_run='{"b":4.2}';%s/calc1.py a=2.1 -h"""
            % dtut,
            res_as=markdown,
            no_cmd_path=True,
        )
        assert 'xxx' in res[0]['res']
        assert not '4.2' in res[0]['res']
        md(
            """
            Up to now there is no indication within the app regarding allowed values for the operator function.
            That is why we accepted the bogus value, when configuring the app."""
        )

    def test_nesting(self):
        t = """
        # Nesting Functional Blocks

        When the app gets more complex you can recursively nest/compose functional blocks into each other

        <from-file: calc_tree.py>
        """
        md(t)
        res = bash_run(
            [
                'calc_tree.py 1 299',
                'calc_tree.py log.level=20 of=mul 100 3',
                'calc_tree.py l.l=20 of=mul 100 3 # shorthand notation for nested blocks',
                'calc_tree.py l.t "hi there" # calling nested functions',
            ]
        )
        r = res[0]['res']
        assert '[10]' in r
        assert '[20]' in r
        assert '300' in r
        for i in 1, 2:
            r = res[i]['res']
            assert not '[10]' in r
            assert '[20]' in r
            assert '300' in r
        r = res[3]['res']
        assert 'hi there' in str(r)
        t = """
        > Of course you could have defined the inner class directly within the main app class as well

        Help output (again with overridden defaults):

        """
        md(t)
        res = bash_run('calc_tree.py l.l=20 l.t.ev=hi of=mul -h')
        assert 'do_testmsg(ev=hi)' in str(res)

    def test_tree_navigation(self):
        t = """
        ## Tree Navigation

        The arrangement of nested classes can be navigated during runtime like so:

        <from-file: calc_tree_nav.py>

        Calling `App.inner.Deep.do_nav_demo()` on a configured tree:
        """
        md(t)
        res = bash_run('calc_tree_nav.py av=100 i.iv=200 i.D.dv=300 i.D.nd')
        r = res[0]['res'].strip()
        assert r == '100 (200, 300)'

    def test_to_dict(self):
        t = """
        # Serializing / PrettyPrint

        Configurative state can be pretty printed and dict-dumped:
        """
        md(t)
        res = bash_run(
            [
                'calc_tree_nav.py av=1 i.D.dv=42 du # du matched to dump',
                'calc_tree_nav.py app_var=2 inner.Deep.deep_var=42 dump asdict=true',  # long form
            ]
        )
        assert res[0]['res'].strip().startswith('App(app_var=1,')

        assert ev(res[1]['res'].strip()) == {
            'app_var': 2,
            'inner': {'Deep': {'deep_var': 42}, 'inner_var': 1},
        }

        md(
            """
        The dict format can be piped as is into a config file for subsequent runs.
        > Currently we do not serialize function parameter changes.
        """
        )

    def test_insert_tutorial_into_readme(self):
        """addd the new version of the rendered tutorial into the main readme"""
        with open(fn) as fd:
            tut = fd.read()

        fnr = here + '/../README.md'
        with open(fnr) as fd:
            readm = fd.read()
        m = '<!-- autogen tutorial -->'
        pre, _, post = readm.split(m)
        with open(fnr, 'w') as fd:
            fd.write(''.join((pre, m, tut, '\n', m, post)))


# ---------------------------------- Tutorial Support Functions and Assignments


Exc = devapps.common.Exc

here = os.path.abspath(os.path.dirname(__file__))
# will contain the tutorial when all tests are run:
fn = here + '/tutorial.md'
if os.path.exists(fn):
    os.unlink(fn)

dtut = here + '/tutorial/'

code = """```code
%s
```"""
# fmt: off
nothing  = lambda s: s
python   = lambda s: code.replace('code', 'python')  % s
bash     = lambda s: code.replace('code', 'bash')  %s
markdown = lambda s: code.replace('code', 'markdown') % (s.replace('```', "``"))
# fmt: on


def del_user_calc_json():
    fn = appdirs.user_config_dir() + '/Calc.json'
    os.unlink(fn) if os.path.exists(fn) else 0


del_user_calc_json()


def md(paras, into=nothing):
    """writes markdown"""
    paras = [paras]
    ctx = {}
    ctx['in_code_block'] = False

    def deindent(p):
        pp = p.replace('\n', '')
        ind = len(pp) - len(pp.lstrip())
        if not ind:
            return p
        return '\n'.join(
            [l[ind:] if not l[:ind].strip() else l for l in p.splitlines()]
        )

    paras = [deindent(p) for p in paras]

    def repl(l, ctx=ctx):
        if '```' in l:
            ctx['in_code_block'] = not ctx['in_code_block']

        ff = '<from-file: '
        if ff in l:
            pre, post = l.split(ff, 1)
            fn, post = post.rsplit('>', 1)
            with open(here + '/tutorial/' + fn) as fd:
                s = fd.read().strip()
            if fn.endswith('.py'):
                s = python(s)
            else:
                s = code % s
            l = pre + s + post
        return l

    r = '\n'.join([repl(l) for para in paras for l in para.splitlines()])
    r = into(r)
    with open(fn, 'a') as fd:
        fd.write('\n' + r)


def bash_run(cmd, res_as=None, no_cmd_path=False, no_show_in_cmd=''):
    """runs unix commands, then writes results into the markdown"""
    if isinstance(cmd, str):
        cmds = [{'cmd': cmd, 'res': ''}]
    elif isinstance(cmd, list):
        cmds = [{'cmd': c, 'res': ''} for c in cmd]
    else:
        cmds = cmd
    orig_cmd = cmds[0]['cmd']
    if not res_as and orig_cmd.startswith('python -c'):
        res_as = python
    D = here + '/tutorial/'

    for c in cmds:
        cmd = c['cmd']
        fncmd = cmd if no_cmd_path else (D + cmd)
        # run it:
        res = c['res'] = sp.getoutput(fncmd)
        if no_show_in_cmd:
            fncmd = fncmd.replace(no_show_in_cmd, '')
        # .// -> when there is no_cmd_path we would get that, ugly:
        # this is just for md output, not part of testing:
        c['cmd'] = fncmd.replace(D, './').strip().replace('.//', './')

    r = '\n\n'.join(['$ %(cmd)s\n%(res)s' % c for c in cmds])

    md(r, into=res_as if res_as else bash)
    return cmds


def appcond_cmd():
    fc = os.popen('which devapp')
    ac = fc.read().strip()
    fc.close()
    return ac, ac.rsplit('/', 1)[0]
