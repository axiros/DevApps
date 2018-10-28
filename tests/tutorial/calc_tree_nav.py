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
