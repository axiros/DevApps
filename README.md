# DevApps - DevOps Ready Applications

[![Build Status][cisvg]][ci] [![Coverage Status][covsvg]][cov] [![PyPI version][pypisvg]][pypi] [![Code style: black][blacksvg]][black]

[cisvg]: https://travis-ci.org/axiros/DevApps.svg?branch=master
[ci]: https://travis-ci.org/axiros/DevApps
[covsvg]: https://codecov.io/github/axiros/DevApps/branch/master/graph/badge.svg
[cov]: https://codecov.io/github/axiros/DevApps
[pypisvg]: https://badge.fury.io/py/DevApps.svg
[pypi]: https://badge.fury.io/py/DevApps
[blacksvg]: https://img.shields.io/badge/code%20style-black-000000.svg
[black]: https://github.com/ambv/black

<!-- badges: http://thomas-cokelaer.info/blog/2014/08/1013/ -->

<!-- autogen tutorial -->


[TOC]

# `devapp`: Command Line Function Configurator and Runner

Given you have a setup like this:

```python
import operator


class Calc:
    """Calculator Demo"""

    oper_func = 'add'

    # One (PY2 compatible) way to provide type hints (optional, for less imperative code):
    def do_run(self, a=int, b=int):
        """Runs operator function on the arguments"""
        return getattr(operator, self.oper_func, self.not_found)(a, b)

    def not_found(self, *a, **kw):
        raise Exception('not supported:', self.oper_func)
```

Via the `devapp` command, you can provide config on the CLI (in addition to
config file and environ) and run this right away:

```bash
$ devapp ./calc.py 41 1
42

$ devapp ./calc.py b=1 41
42

$ devapp ./calc.py oper_func=mul a=2 b=100
200

$ devapp ./calc.py of=mul a=2 b=150
300

$ export Calc_oper_func=mul Calc_run='{"a":100}'; devapp ./calc.py  b=4
400

$ devapp ./calc.py a=1 b=foo # b has wrong type
0.02276 [error    ] Cannot cast expected_type=int for_param=b got=foo

$ devapp ./calc.py # missing params
0.01920 [error    ] Value required param=a type=int
0.01957 [error    ] Value required param=b type=int

$ devapp ./calc.py of=mul -h # help output

# Calc

Calculator Demo

## Parameters

| Name      | Val | F | Dflt | Descr | Expl |
| --------- | --- | - | ---- | ----- | ---- |
| oper_func | mul | C | add  |       |      |

## Actions

### run

Runs operator function on the arguments

> do_run(a=<int>, b=<int>)
```


# `@app`: Converts Class Trees

The decorator variant allows to run the application standalone:

```python
#!/usr/bin/env python

import operator
from devapps.app import app  # one way of usage is via this decorator


@app  # apply the decorator to your app holding class
class Calc:
    """Calculator Demo"""

    oper_func = 'add'

    def do_run(calc, a=int, b=int):
        """Runs operator function on the arguments"""
        return getattr(operator, calc.oper_func, calc.not_found)(a, b)

    def not_found(calc, *a, **kw):
        raise Exception('not supported:', calc.oper_func)
```

We
- added a hashbang and made the file executable.
- decorated the toplevel class.

We can run the thing now from the CLI, directly:


```bash
$ ./calc1.py a=2 b=4
6

$ ./calc1.py b=2 a=4 # mappable so supported
6

$ ./calc1.py 2 4.1 # positionally given, rounded
6

$ ./calc1.py a=2 4.1 # mapping found
6

$ ./calc1.py oper_func=mul a=2 b=4
8

$ ./calc1.py of=mul a=2 b=4 # short form for oper_func
8
```

## More Actions

A class may have more action functions (by default prefixed with `do_`.
`do_run` was just the default action - run if no other is configured.

Lets add another one:

```python
#!/usr/bin/env python

import operator
from devapps.app import app  # one way of usage is via this decorator


@app  # apply the decorator to your app holding class
class Calc:
    """Calculator Demo"""

    oper_func = 'add'

    op = lambda calc: getattr(operator, calc.oper_func, calc.not_found)

    def do_run(calc, a=int, b=int):
        """Runs operator function on the arguments"""
        return calc.op()(a, b)

    def do_list_sum(calc, args=[0]):
        """Sums up all numbers given"""
        return sum(args)

    def not_found(calc, *a, **kw):
        raise Exception('not supported:', calc.oper_func)
```

and run it:
```bash
$ ./calc2.py list_sum "1,2,3"
6

$ ./calc2.py ls "1, 2, 3" # short form for function supported
6
```

## Help Output

`-h` delivers a markdown formatted help output:
```markdown
$ ./calc2.py -h

# Calc

Calculator Demo

## Parameters

| Name      | Val | F | Dflt | Descr | Expl |
| --------- | --- | - | ---- | ----- | ---- |
| oper_func | add |   |      |       |      |

## Actions

### list_sum

Sums up all numbers given

> do_list_sum(args=[0])

### run

Runs operator function on the arguments

> do_run(a=<int>, b=<int>)
```

### Markdown?

Because this allows to add a lot of structuring information - which we can use to nicely colorize the output, provide TOCs, put into README's and so on.

`-hc` shows the implementation:
```markdown
$ ./calc2.py -hc

# Calc

Calculator Demo

## Parameters

| Name      | Val | F | Dflt | Descr | Expl |
| --------- | --- | - | ---- | ----- | ---- |
| oper_func | add |   |      |       |      |

## Actions

### list_sum

Sums up all numbers given

``python=
def do_list_sum(calc, args=[0]):
    return sum(args)
``

### run

Runs operator function on the arguments

``python=
def do_run(calc, a=int, b=int):
    return calc.op()(a, b)
``
```

> If the terminal width is not wide enough for the parameter tables we render the parameters vertically.
> `-hu` (classic unix) forces this always.

### Defaults Are Configurable
Lets check `-h` output when arguments are supplied:
```markdown
$ ./calc2.py of=multiply 1 -h | head -n 10

# Calc

Calculator Demo

## Parameters

| Name      | Val      | F | Dflt | Descr | Expl |
| --------- | -------- | - | ---- | ----- | ---- |
| oper_func | multiply | C | add  |       |      |
```

As you can see our value from the CLI made it into the documentation.  
The `F` (From) column shows where the value was comming from.

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

```python
$ python -c "if 1:
        cfg = {'oper_func': 'mul', 'run': {'a': 10.3}}

        # write to user config dir:
        from appdirs import user_config_dir as ucd
        from json import dumps
        with open(ucd() + '/Calc.json', 'w') as fd:
            fd.write(dumps(cfg))"
```
Now we can run the app *without* supplying `a` and get a multiplication:
```bash
$ ./calc1.py b=42
420
```
> Positionally you could overwrite `a` still on the CLI, so we do not map one value only to `b`
```bash
$ ./calc1.py 5 42
210
```
```bash
$ ./calc1.py 5
0.03109 [error    ] Value required param=b type=int
```
Here is the output of `-h`:
```markdown
$ ./calc1.py -h

# Calc

Calculator Demo

## Parameters

| Name      | Val | F | Dflt | Descr | Expl |
| --------- | --- | - | ---- | ----- | ---- |
| oper_func | mul | F | add  |       |      |

## Actions

### run

Runs operator function on the arguments
:::warning
Defaults modified (by File):
- a: 10 (was <int>)
:::

> do_run(a=10, b=<int>)
```
Again the app was reconfigured - this time by the config file (F)

Observe the int value - it was converted from the float, since that is what the function explicitly asked for.
> Yes, we did mutate inplace the defaults of the `Calc.do_run` function - i.e. process wide!
> Keep this in mind when using that feature - reading the source code is then misleading.
> Help output shows modifications and origin rather prominently as you can see.

We delete the file for now.

## Environ

Supported as well - but you have to provide structed values in lit.eval form:
```bash
$ export Calc_oper_func=mul Calc_run='{"a":4.2}'; ./calc1.py b=3
12
```

> By default we do NOT support short forms at the environ provider and also we are case sensitive.
> Note that the overridden defaults still had been casted to the original types of the function signature.


Help output, as expected:
```markdown
$ export Calc_oper_func=xxx Calc_run='{"b":4.2}';./calc1.py a=2.1 -h

# Calc

Calculator Demo

## Parameters

| Name      | Val | F | Dflt | Descr | Expl |
| --------- | --- | - | ---- | ----- | ---- |
| oper_func | xxx | E | add  |       |      |

## Actions

### run

Runs operator function on the arguments
:::warning
Defaults modified (by Env):
- b: 4 (was <int>)
:::

> do_run(a=<int>, b=4)
```

Up to now there is no indication within the app regarding allowed values for the operator function.
That is why we accepted the bogus value, when configuring the app.

# Nesting Functional Blocks

When the app gets more complex you can recursively nest/compose functional blocks into each other

```python
#!/usr/bin/env python

import operator
from devapps.app import app


class Log:
    """Print Logger"""

    level = 10

    def do_testmsg(log, ev='hello'):
        log.msg(30, ev)
        return ''

    def msg(log, level, ev, **kw):
        if level >= log.level:
            print('[%s] %s %s' % (level, ev, kw))


@app
class Calc:
    """Calculator Demo"""

    oper_func = 'add'
    log = Log

    def do_run(calc, a=int, b=int):
        """Runs operator function on the arguments"""
        of = calc.oper_func
        calc.log.msg(10, 'Calculating', operation=of, a=a, b=b)
        res = getattr(operator, of, calc.not_found)(a, b)
        calc.log.msg(20, 'Returning', result=res)
        return res

    def not_found(calc, *a, **kw):
        raise Exception('not supported:', calc.oper_func)
```
```bash
$ ./calc_tree.py 1 299
[10] Calculating {'operation': 'add', 'a': 1, 'b': 299}
[20] Returning {'result': 300}
300

$ ./calc_tree.py log.level=20 of=mul 100 3
[20] Returning {'result': 300}
300

$ ./calc_tree.py l.l=20 of=mul 100 3 # shorthand notation for nested blocks
[20] Returning {'result': 300}
300

$ ./calc_tree.py l.t "hi there" # calling nested functions
[30] hi there {}
```

> Of course you could have defined the inner class directly within the main app class as well

Help output (again with overridden defaults):

```bash
$ ./calc_tree.py l.l=20 l.t.ev=hi of=mul -h

# Calc

Calculator Demo

## Parameters

| Name      | Val | F | Dflt | Descr | Expl |
| --------- | --- | - | ---- | ----- | ---- |
| oper_func | mul | C | add  |       |      |

## Actions

### run

Runs operator function on the arguments

> do_run(a=<int>, b=<int>)

---
## log

Print Logger

### Parameters

| Name  | Val | F | Dflt | Descr | Expl |
| ----- | --- | - | ---- | ----- | ---- |
| level | 20  | C | 10   |       |      |

### Actions

#### testmsg

:::warning
Defaults modified (by CLI):
- ev: hi (was hello)
:::

> do_testmsg(ev=hi)
```

## Tree Navigation

The arrangement of nested classes can be navigated during runtime like so:

```python
#!/usr/bin/env python
from __future__ import print_function  # for Python2

import operator
import attr
from devapps import root, parent, as_dict
from devapps import app


class Inner:
    inner_var = 1

    def do_nav_demo(inner):
        return root(inner).do_run(inner.inner_var, inner.Deep.deep_var)

    class Deep:
        deep_var = 2

        def do_nav_demo(deep):
            print(root(deep).app_var, parent(deep).do_nav_demo())
            return ''


@app.app
class App:
    inner = Inner
    app_var = 0

    def do_run(app, a=1, b=2):
        return a, b

    def do_dump(app, asdict=False):
        print(app if not asdict else as_dict(app))
        return ''
```

Calling `App.inner.Deep.do_nav_demo()` on a configured tree:
```bash
$ ./calc_tree_nav.py av=100 i.iv=200 i.D.dv=300 i.D.nd
100 (200, 300)
```

# Serializing / PrettyPrint

Configurative state can be pretty printed and dict-dumped:
```bash
$ ./calc_tree_nav.py av=1 i.D.dv=42 du # du matched to dump
App(app_var=1, inner=Inner(Deep=Inner.Deep(deep_var=42), inner_var=1))


$ ./calc_tree_nav.py app_var=2 inner.Deep.deep_var=42 dump asdict=true
{'app_var': 2, 'inner': {'Deep': {'deep_var': 42}, 'inner_var': 1}}
```

The dict format can be piped as is into a config file for subsequent runs.
> Currently we do not serialize function parameter changes.
<!-- autogen tutorial -->


# Credits

[Hynek Schlawack](https://hynek.me/):

- [structlog][structlog]
- [attrs][attrs]

Testing/CI:

- [pytest](https://github.com/pytest-dev/pytest/graphs/contributors)
- [codecov][cov]
- [travis][ci]

[structlog]: https://github.com/hynek/structlog
[attrs]: https://github.com/python-attrs/attrs



# Alternatives

There are already tons of options to get the CLI parsed:

- [click](https://pypi.org/project/click/)
- [docopt](https://github.com/docopt/docopt)
- [argparse](https://docs.python.org/3/library/argparse.html) Stdlib
- [argh](https://github.com/neithere/argh/) 

Further great libs, as from the argh docs:

- [argdeclare](http://code.activestate.com/recipes/576935-argdeclare-declarative-interface-to-argparse/)
- [argparse-cli](http://code.google.com/p/argparse-cli/)
- [django-boss](https://github.com/zacharyvoase/django-boss/tree/master/src/)
  seems to lack support for nested commands and is strictly Django-specific.
- [entrypoint](http://pypi.python.org/pypi/entrypoint/) is lightweight
- [opster](http://pypi.python.org/pypi/opster/) and
  [finaloption](http://pypi.python.org/pypi/finaloption/) support
  nested commands but are based on the outdated optparse library and
  therefore reimplement some features available in argparse.
- [simpleopt](http://pypi.python.org/pypi/simpleopt/)
- [opterator](https://github.com/buchuki/opterator/) is based on the
  outdated optparse and does not support nested commands.
- [clap](http://pypi.python.org/pypi/Clap/)
- [plac](http://micheles.googlecode.com/hg/plac/doc/plac.html) is a
  very powerful alternative to argparse.
- [baker](http://pypi.python.org/pypi/Baker/)
- [plumbum](http://plumbum.readthedocs.org/en/latest/cli.html)
- [docopt](http://docopt.org)
- [aaargh](http://pypi.python.org/pypi/aaargh)
- [cliff](http://pypi.python.org/pypi/cliff)
- [cement](http://builtoncement.com/2.0/)

Seems like *every man should plant a tree, raise a son and write a command line parser.*



