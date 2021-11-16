import functools
from tinyolap.rules import RuleScope

def rule(cube: str, pattern: list[str], scope: RuleScope = RuleScope.ALL_LEVELS, volatile: bool = False):
    """
    Decorator for TinyOlap rule functions.

    :param cube: The cube the rule should be assigned to.
    :param pattern: The cell pattern that should trigger the rule. Either a single member name or a list
                    of member names from different dimensions.
    :param scope: The scope of the rule. Please refer the documentation for further details.
    :param volatile: (optional, default = False) Identifies that the rule may or will return changing
                     results on identical input, e.g. if real-time data integration is used.
    """
    def decorator_rule(func):
        @functools.wraps(func)
        def wrapper_rule(*args, **kwargs):
            return func(*args, **kwargs)
        # wrapper_rule.server = Server()
        # wrapper_rule.server._register(func, database, cube, pattern, scope)
        wrapper_rule.cube = cube
        wrapper_rule.pattern = pattern
        wrapper_rule.scope = scope
        wrapper_rule.volatile = volatile
        return wrapper_rule
    return decorator_rule
