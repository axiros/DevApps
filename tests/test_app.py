import pytest
import sys
from devapps.app import app, root
from devapps import common

if common.PY2:
    from StringIO import StringIO
else:
    from io import StringIO


def restore_argv(oav):
    while sys.argv:
        sys.argv.pop()
    sys.argv.extend(oav)


def test_deco_no_args(capsys):
    class Calc:
        def do_run(calc, a, b):
            return a, b

        def do_list(calc, a, *b):
            return a, b

        class inner:
            def do_inner(inner, a, b):
                return root(inner).do_run(a, b)

    cfg = dict(common.CFG)
    oav = list(sys.argv)
    sys.argv = ['_', '1', '2']
    old_stdout = sys.stdout
    sys.stdout = out = StringIO()
    try:
        app1 = app(Calc)  # runs already the app but we can't get result
        assert out.getvalue().strip() == "('1', '2')"
    finally:
        restore_argv(oav)
        sys.stdout = old_stdout
        # we populated the logger, i.e. changed global state:
        # which other tests assume to be clean:
        common.CFG = cfg
