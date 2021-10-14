import enum
import inspect


class RuleScope(enum.Enum):
    """
    Defines the scope of a rule. Meaning, to which level of data the rule should be applied.
    """

    #: (default) Indicates that the rule should be executed for base level and aggregated level cells.
    ALL_LEVELS = 0
    #: Indicates that the rule should be executed for aggregated level cells only.
    AGGREGATION_LEVEL = 1
    #: Indicates that the rule should be executed for base level cells only.
    BASE_LEVEL = 2
    #: Indicates that the rule should replace the base level cell value from the database by the results of
    #: the rule. This can dramatically slow down aggregation speed. Requires a special trigger to be set.
    ROLL_UP = 3
    #: Indicates that these rules should be executed when cell values are set or changed.
    #: This is useful for time consuming calculations which may be *too expensive* to run at idx_address time.
    ON_ENTRY = 4
    #: Indicates that these rules need to be invoked by a command. Requires the decorator parameter 'command'
    # to be specified.
    COMMAND = 5

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def __hash__(self):
        return hash(self.value)

class Rules:
    """Rules define custom calculation or business logic to be assigned to a cube.

    Rules consist two main components:
    * A trigger or pattern, defining the context for which the rule should be executed
    * A scope, defining to which level of data the rule should be applied.
      Either for base level cells, aggregated cells, all cells or on write back of values.
    * A function, defining the custom calculation or business logic. This can be any Python method or function.

    .. information::
        Rules functions have to be implemented as a simple Python function with just one single parameter and
        a return value. The single parameter should be called 'c' and will contain an TinyOlap Cell, representing
        the current cell context the rule should be calculated for.

        What happens in a rule function, is up totally to the programmer. The value returned by rules function
        can either be a certain value (most often a numerical number, but can be anything) or one of the following
        constants which are directly available from within a cursor object.

        * **NONE** - Indicates that rules function was not able return a proper result (why ever).
        * **CONTINUE** - Indicates that either subsequent rules should continue and do the calculation work
           or that the cell value, either from a base-level or an aggregated cell, form the underlying cube should
           be used.
        * **ERROR** - Indicates that the rules functions run into an error. Such errors will be pushed up to initially
          calling cell request.

        Sample of a proper rule:

        .. code:: python
            def rule_average_price(c : tinyolap.context):
                quantity = c["quantity"]
                sales = c["sales"]
                # ensure both values exist or are of the expected type (cell values can be anything)
                if quantity is float and sales is float:
                    if quantity != 0.0:
                        return sales / quantity
                    return "n.a."  # the developer decided to return some text, what is totally fine.
                return c.CONTINUE
    """

    def __init__(self):
        self.any: bool = False
        self.functions = []
        self.function_names = []
        self.function_scopes = []
        self.source = []
        self.pattern = []
        self.pattern_idx = []

    def __bool__(self):
        return self.functions is True

    def __len__(self):
        return len(self.functions)

    def register(self, function, function_name: str,
                 pattern: list[str], idx_pattern: list[tuple[int, int]], scope: RuleScope):
        """
        Registers a rules function (a Python method or function).

        :param scope: The scope of the rule function.
        :param function_name: Name of the rule function.
        :param function: The Python rule function to execute.
        :param pattern: The cell pattern to trigger the rule function.
        :param idx_pattern: The cell index pattern to trigger the rule function.
        """
        self.functions.append(function)
        self.function_names.append(function_name)
        self.function_scopes.append(scope)
        self.pattern.append(pattern)
        self.source.append(self._get_source(function))
        self.pattern_idx.append(idx_pattern)
        self.any = True

    @staticmethod
    def _get_source(function):
        lines = inspect.getsource(function)
        return lines

    def first_match(self, idx_address) -> (bool, object):
        """
        Returns the first pattern match, if any, for a given cell address.

        :param idx_address: The cell address in index format.
        :return: Returns a tuple (True, *function*) if at least one pattern matches,
        *function* is the actual rules function to call, or (False, None) if none
        of the patterns matches the given cell address.
        """
        for idx, function_pattern in enumerate(self.pattern_idx):  # e.g. [(0,3),(3,2)] >> dim0 = member3, dim3 = member2
            for dim_pattern in function_pattern:   # e.g. (0,3) >> dim0 = member3
                if idx_address[dim_pattern[0]] != dim_pattern[1]:
                    break
            else:
                return True, self.functions[idx]  # this will be executed only if the inner loop did NOT break
        return False, None

