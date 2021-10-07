import functools
from tinyolap.server import Server


def register(database: str, cube: str, pattern: list[str] ):
    def decorator_register(func):
        @functools.wraps(func)
        def wrapper_register(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper_register.server = Server()
        wrapper_register.server._register(func, database, cube, pattern)
        return wrapper_register
    return decorator_register


class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.num_calls = 0

    def __call__(self, *args, **kwargs):
        self.num_calls += 1
        print(f"Call {self.num_calls} of {self.func.__name__!r}")
        return self.func(*args, **kwargs)