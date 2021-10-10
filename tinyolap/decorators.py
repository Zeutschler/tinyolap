import functools

from tinyolap.rules import RuleScope
from tinyolap.server import Server


def rule(cube: str, pattern: list[str], scope: RuleScope = RuleScope.ALL_LEVELS):
    def decorator_rule(func):
        @functools.wraps(func)
        def wrapper_rule(*args, **kwargs):
            return func(*args, **kwargs)
        # wrapper_rule.server = Server()
        # wrapper_rule.server._register(func, database, cube, pattern, scope)
        wrapper_rule.cube = cube
        wrapper_rule.pattern = pattern
        wrapper_rule.scope = scope
        return wrapper_rule
    return decorator_rule


class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.num_calls = 0

    def __call__(self, *args, **kwargs):
        self.num_calls += 1
        print(f"Call {self.num_calls} of {self.func.__name__!r}")
        return self.func(*args, **kwargs)