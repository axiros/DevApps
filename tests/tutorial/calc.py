import operator


class Calc:
    """Calculator Demo"""

    oper_func = 'add'

    def do_run(self, a=int, b=int):
        """Runs operator function on the arguments"""
        return getattr(operator, self.oper_func, self.not_found)(a, b)

    def not_found(self, *a, **kw):
        raise Exception('not supported:', self.oper_func)
