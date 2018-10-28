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
