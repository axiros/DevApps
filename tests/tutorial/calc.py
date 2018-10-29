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
