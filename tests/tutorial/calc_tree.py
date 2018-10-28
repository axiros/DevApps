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
