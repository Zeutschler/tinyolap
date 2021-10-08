import enum
import inspect

#todo: get (relevant) code from rules.py in here.

class BaseFunction:
    """
    Base class for the implementation of TinyOlap functions.
    """
    pass


class Functions:

    class FormulaType(enum.Enum):
        UNIVERSAL = 0
        PUSH_DOWN = 1
        AGGREGATION = 2

    def __init__(self):
        self.any: bool = False
        self.functions = []
        self.source = []
        self.pattern = []
        self.pattern_idx = []

    def register(self, func, pattern: list[str], pattern_idx: list[tuple[int, int]]):
        self.functions.append(func)
        self.pattern.append(pattern)
        self.source.append(self._get_source(func))
        self.pattern_idx.append(pattern_idx)
        self.any = True

    @staticmethod
    def _get_source(func):
        lines = inspect.getsource(func)
        # check if first line is inserted
        return lines

    def first_match(self, address) -> (bool, object):
        for idx, func_pattern in enumerate(self.pattern_idx):  # e.g. [(0,3),(3,2)] >> dim0 = member3, dim3 = member2
            for dim_pattern in func_pattern:   # e.g. (0,3) >> dim0 = member3
                if address[dim_pattern[0]] != dim_pattern[1]:
                    break
            else:
                return True, self.functions[idx]  # only executed if the inner loop did NOT break
        return False, None

