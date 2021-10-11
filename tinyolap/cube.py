import collections
from collections.abc import Iterable, Sized
from inspect import isroutine

import tinyolap.rules
from case_insensitive_dict import CaseInsensitiveDict
from cursor import Cursor
from tinyolap.custom_errors import *
from tinyolap.fact_table import FactTable
from tinyolap.dimension import Dimension
from tinyolap.rules import Rules, RuleScope


class Cube:
    """Represents a multi-dimensional table."""
    __magic_key = object()

    @classmethod
    def create(cls, backend, name: str, dimensions: list[Dimension], measures: list[str]):
        cube = Cube(Cube.__magic_key, name, dimensions, measures)
        cube._backend = backend
        cube._backend_table = backend.add_cube(name, dimensions, cube._measures.values())
        return cube

    def __init__(self, cub_creation_key, name: str, dimensions, measures):
        """
        NOT INTENDED FOR DIRECT USE! Cubes and dimensions always need to be managed by a Database.
        Use method 'Database.add_cube(...)' to create objects type Cube.

        :param name:
        :param dimensions:
        :param measures:
        """
        assert (cub_creation_key == Cube.__magic_key), \
            "Objects of type Cube can only be created through the method 'Database.add_cube()'."

        self._name = name
        self._dim_count = len(dimensions)
        self._dimensions = tuple(dimensions)
        self._dim_names = []
        self._dim_lookup = CaseInsensitiveDict([(dim.name, idx) for idx, dim in enumerate(dimensions)])
        self._facts = FactTable(self._dim_count, self)

        self._rules_all_levels = Rules()
        self._rules_base_level = Rules()
        self._rules_aggr_level = Rules()
        self._rules_roll_up = Rules()
        self._rules_on_entry = Rules()

        # create a default-measure if none is defined
        if not measures:
            measures = ["value"]
        self._measures = {}
        for idx, measure in enumerate(measures):
            self._measures[measure] = idx
        self._default_measure = measures[0]

        # initialize a default-measure if none is defined

        self._cell_requests = 0
        self._caching = True
        self._cache = {}

    def __str__(self):
        return f"cube '{self.name}'"

    def __repr__(self):
        return f"cube '{self.name}'"

    # region Rules
    def remove_rule(self, pattern: list[str]) -> bool:
        """
        Removes (unregisters) a rule function from the cube.

        :param pattern: The pattern of the rule to be removed.
        :return: ``True``, if a function with the given pattern was found and removed, ``False`` otherwise.
        """
        return NotImplemented

    def remove_all_rules(self):
        """
        Removes all rule functions from the cube.
        """
        return NotImplemented

    def add_rule(self, function, pattern: list[str] = None, scope: RuleScope = None):
        """
        Registers a rule function for the cube. Rules function either need to be decorated with the ``@rules(...)``
        decorator or the arguments ``pattern`` and ``scope`` of the ``add_rules(...)`` function must be specified.

        :param function: The rules function to be called.
        :param pattern: The cell address pattern that should trigger the rule.
        :param scope: The scope of the rule.
        """
        offset = 0
        if not isroutine(function):
            if callable(function) and function.__name__ == "<lambda>":
                offset = 1
            else:
                raise RuleError(f"Argument 'function' does not seem to be a Python function, tpye id '{type(function)}'.")

        # validate function and decorator parameters
        function_name = str(function).split(" ")[1 + offset]
        cube_name = self.name
        if hasattr(function, "cube"):
            cube_name = function.cube
            if cube_name.lower() != self.name.lower():
                raise RuleError(
                    f"Failed to add rule function. Function '{function_name}' does not seem to be associated "
                    f"with this cube '{self.name}', but with cube '{cube_name}'.")
        if not pattern:
            if hasattr(function, "pattern"):
                pattern = function.pattern
                if type(pattern) is str:
                    pattern = [pattern, ]
                if not type(pattern) is list:
                    raise RuleError(f"Failed to add rule function. Argument 'pattern' is not of the expected "
                                    f"type 'list(str)' but of type '{type(pattern)}'.")
            else:
                raise RuleError(f"Failed to add rule function. Argument 'pattern' missing for "
                                f"function {function_name}'. Use the '@rule(...) decorator from tinyolap.decorators.")
        if not scope:
            if hasattr(function, "scope"):
                scope = function.scope
                if not type(scope) is RuleScope:
                    raise RuleError(f"Failed to add rule function. Argument 'scope' is not of the expected "
                                    f"type 'RuleScope' but of type '{type(scope)}'.")
            else:
                raise RuleError(f"Failed to add rule function. Argument 'scope' missing for "
                                f"function {function_name}'. Use the '@rule(...) decorator from tinyolap.decorators.")

        if type(pattern) is str: # a lazy user forgot to put the apptern in brackets
            pattern = [pattern, ]

        idx_pattern = self.__pattern_to_idx_pattern(pattern)

        if scope == RuleScope.ALL_LEVELS:
            self._rules_all_levels.register(function, function_name, pattern, idx_pattern, scope)
        elif scope == RuleScope.AGGREGATION_LEVEL:
            self._rules_aggr_level.register(function, function_name, pattern, idx_pattern, scope)
        elif scope == RuleScope.BASE_LEVEL:
            self._rules_base_level.register(function, function_name, pattern, idx_pattern, scope)
        elif scope == RuleScope.ROLL_UP:
            self._rules_roll_up.register(function, function_name, pattern, idx_pattern, scope)
        elif scope == RuleScope.ON_ENTRY:
            self._rules_on_entry.register(function, function_name, pattern, idx_pattern, scope)
        else:
            raise RuleError(f"Unexpected value '{str(scope)}' for argument 'scope'.")

    def __pattern_to_idx_pattern(self, pattern):
        """
        Converts a pattern into it's index representation.

        :param pattern: The pattern to be converted.
        :return: The index pattern.
        """
        if type(pattern) is str:
            pattern = list((pattern,))
        # Sorry, miss-use of cursor. All the effort just to use the 'c._get_member(p)' function
        address = self._get_default_cell_address()
        c = self._create_cursor_from_bolt(address, self.__to_bolt(address))
        # create something like this: idx_pattern = [(0, 3)]
        idx_pattern = []
        for p in pattern:
            idx_dim, idx_member, member_level = c._get_member(p)
            idx_pattern.append((idx_dim, idx_member))
        return idx_pattern

    # endregion

    # region Properties
    @property
    def name(self) -> str:
        """Returns the name of the cube."""
        return self._name

    @property
    def cell_requests(self) -> int:
        """Returns the number"""
        return self._cell_requests

    def reset_cell_requests(self):
        """Identifies if caching is activated for the current cube.
        By default, caching is activated for all cubes."""
        self._cell_requests = 0

    @property
    def caching(self) -> bool:
        """Identifies if caching is activated for the current cube.
        By default, caching is activated for all cubes."""
        return self._caching

    @caching.setter
    def caching(self, value: bool):
        """Identifies if caching is activated for the current cube.
        By default, caching is activated for all cubes."""
        self._caching = value
        if not self._caching:
            self._cache = {}

    @property
    def dimensions_count(self) -> int:
        """Returns the number of dimensions of the cube."""
        return self._dim_count

    @property
    def measures_count(self) -> int:
        """Returns the number of measures of the cube."""
        return len(self._measures)

    @property
    def default_measure(self) -> str:
        """Returns/sets the default measure of the cube.
        By default, this is always the first measure from the list of measures."""
        return self._default_measure

    @default_measure.setter
    def default_measure(self, value: str):
        """Returns/sets the default measure of the cube.
        By default, this is always the first measure from the list of measures."""
        if value not in self._measures:
            raise KeyNotFoundError(f"Failed to set default member. "
                                   f"'{value}' is not a measure of cube '{self._name}'.")
        self._default_measure = value

    @property
    def measures(self) -> list[str]:
        """Returns the list of measures of a cube."""
        return [str(self._measures.keys())]

    # endregion

    # region Dimension and Measures related methods
    def get_measures(self) -> list[str]:
        """Returns the list of measures of a cube."""
        return list(self._measures.keys())

    def get_dimension_by_index(self, index: int):
        """Returns a dimension from a cubes list of dimensions at the given index."""
        if (index < 0) or (index > self._dim_count):
            raise ValueError(f"Requested dimension index '{index}' is out of range [{0}, {self._dim_count}].")
        return self._dimensions[index]

    def get_dimension_ordinal(self, name: str):
        """Returns the ordinal position of a dimension with the cube definition.
        :return The ordinal position of the dimension, if the dimension is contained ones in the cube.
                A list of ordinal positions if the dimension is contained multiple times in the cube.
        """
        ordinals = []
        for idx, dim_name in enumerate([dim.name for dim in self._dimensions]):
            if name == dim_name:
                ordinals.append(idx)
        if not ordinals:
            return -1
        if len(ordinals) == 1:
            return ordinals[0]
        return ordinals

    def get_dimension(self, name: str):
        """Returns the dimension defined for the given dimension index."""
        result = [dim for dim in self._dimensions if dim.name == name]
        if not result:
            raise ValueError(f"Requested dimension '{name}' is not a dimension of cube {self.name}.")
        return result[0]

    # endregion

    # region Cell access via indexing/slicing
    def __getitem__(self, item):
        bolt = self.__to_bolt(item)
        return self._get(bolt)

    def __setitem__(self, item, value):
        bolt = self.__to_bolt(item)
        self._set(bolt, value)

    def __delitem__(self, item):
        bolt = self.__to_bolt(item)
        self._set(bolt, None)

    # endregion

    # region Read and write values

    # FOR FUTURE USE...
    # def get_value_by_bolt(self, bolt: tuple):
    #     """Returns a value from the cube for a given idx_address and measure.
    #     If no records exist for the given idx_address, then 0.0 will be returned."""
    #     return self.__get(bolt)
    # def get_bolt(self, *keys:str):
    #     return self.__to_bolt(keys)

    def __to_bolt(self, keys):
        """Converts a given idx_address, incl. member and (optional) measures, into a bolt.
        A bolt is a tuple of integer keys, used for internal access of cells.
        """

        dim_count = self._dim_count
        measures_count = len(keys) - dim_count
        if measures_count < 0:
            raise InvalidCellAddressError(f"Invalid idx_address. At least {self._dim_count} members expected "
                                          f"for cube '{self._name}, but only {len(keys)} where passed in.")
        # Validate members
        dimensions = self._dimensions
        idx_address = [None] * dim_count
        super_level = 0
        for i, member in enumerate(keys[: dim_count]):
            if member in dimensions[i].member_idx_lookup:
                idx_address[i] = dimensions[i].member_idx_lookup[member]
                super_level += dimensions[i].members[idx_address[i]][6]
            else:
                raise InvalidCellAddressError(f"Invalid idx_address. '{member}' is not a member of the {i}. "
                                              f"dimension '{dimensions[i].name}' in cube {self._name}.")
        idx_address = tuple(idx_address)

        # validate measures (if defined)
        if measures_count == 0:
            idx_measures = self._measures[self._default_measure]
        else:
            idx_measures = []
            for measure in keys[self._dim_count:]:
                if measure not in self._measures:
                    raise InvalidCellAddressError(f"'{measure}' is not a measure of cube '{self.name}'.")
                idx_measures.append(self._measures[measure])
            if measures_count == 1:
                idx_measures = idx_measures[0]
            else:
                idx_measures = tuple(idx_measures)

        return super_level, idx_address, idx_measures  # that's the 'bolt'

    def get(self, address: tuple):
        """Reads a value from the cube for a given idx_address.
        If no records exist for the given idx_address, then 0.0 will be returned.
        :raises InvalidKeyError:
        """
        bolt = self.__to_bolt(address)
        return self._get(bolt)

    def set(self, address: tuple, value):
        """Writes a value to the cube for the given bolt (idx_address and measures)."""
        bolt = self.__to_bolt(address)
        return self._set(bolt, value)

    def _get(self, bolt):
        """Returns a value from the cube for a given idx_address and measure.
        If no records exist for the given idx_address, then 0.0 will be returned."""
        (super_level, idx_address, idx_measures) = bolt

        if self._rules_all_levels.any:
            found, func = self._rules_all_levels.first_match(idx_address)
            if found:
                cursor = self._create_cursor_from_bolt(None, (super_level, idx_address, idx_measures))
                try:
                    value = func(cursor)
                    if value != Cursor.CONTINUE:
                        return value
                except Exception as e:
                    raise RuleError(f"Function {func.__name__} failed. {str(e)}")

        if super_level == 0:  # base-level cells
            if type(idx_measures) is int:
                self._cell_requests += 1
                return self._facts.get(idx_address, idx_measures)
            else:
                self._cell_requests += len(idx_measures)
                return [self._facts.get(idx_address, m) for m in idx_measures]

        else:  # aggregated cells
            if self._caching and bolt in self._cache:
                self._cell_requests += 1
                return self._cache[bolt]

            # get records row ids for current cell idx_address
            rows = self._facts.query(idx_address)

            # aggregate records
            if type(idx_measures) is int:
                if not rows:
                    return 0.0
                facts = self._facts.facts
                total = 0.0
                for row in rows:
                    if idx_measures in facts[row]:
                        value = facts[row][idx_measures]
                        if type(value) is float:
                            total += value

                self._cell_requests += len(rows)
                if self._caching:
                    self._cache[bolt] = total  # save value to cache

                return total
            else:
                if not rows:
                    return [0.0] * len(idx_measures)
                facts = self._facts.facts
                totals = [] * len(idx_measures)
                for idx, idx_m in idx_measures:
                    for row in rows:
                        if idx_m in facts[row]:
                            value = facts[row][idx_m]
                            if type(value) is float:
                                totals[idx] += value

                self._cell_requests += len(rows) * len(idx_measures)
                if self._caching:
                    self._cache[bolt] = totals  # save value to cache
                return totals

    def _set(self, bolt, value):
        """Writes a value to the cube for the given bolt (idx_address and measures)."""
        if self._caching and self._cache:
            self._cache = {}  # clear the cache

        (super_level, idx_address, idx_measures) = bolt

        if super_level == 0:  # for base-level cells...
            if type(idx_measures) is int:
                result = self._facts.set(idx_address, idx_measures, value)
            elif isinstance(idx_measures, collections.abc.Sequence):
                if isinstance(value, collections.abc.Sequence):
                    if len(idx_measures) != len(value):
                        raise InvalidKeyError(f"Arguments for write back not aligned. The numbers of measures "
                                              f"and the numbers of values handed in need to be identical.")
                    result = all([self._facts.set(idx_address, m, v) for m, v in zip(idx_measures, value)])
                else:
                    result = all([self._facts.set(idx_address, m, value) for m in idx_measures])

            #  ...check for base-level (push) rules to be executed
            # todo: Add push rules
            # if self._rules_all_levels:
            #     success = self._rules_all_levels.on_set(super_level, idx_address, idx_measures, value)
            #     if success:
            #         return success

            return True
        else:
            raise InvalidOperationError(f"Write back to aggregated cells in not (yet) supported.")

    def _update_aggregation_index(self, fact_table_index, address, row):
        """Updates all fact table index for all aggregations over all dimensions. FOR INTERNAL USE ONLY!"""
        # please note that a '__' name prefix is not possible
        # as this function is called through a weak reference.
        for d, idx_member in enumerate(address):
            for idx_parent in self._dimensions[d].members[address[d]][self._dimensions[d].ALL_PARENTS]:
                if idx_parent in fact_table_index._index[d]:
                    fact_table_index._index[d][idx_parent].add(row)
                else:
                    fact_table_index._index[d][idx_parent] = {row}

    def _validate_address(self, address: tuple, measure):
        """Validates a given idx_address and measures and return the according indexes."""
        if type(measure) is str:
            if measure not in self._measures:
                raise ValueError(f"'{measure}' is not a measure of cube '{self.name}'.")
            idx_measure = self._measures[measure]
        elif isinstance(measure, Iterable):
            idx_measure = []
            for m in measure:
                if m not in self._measures.keys():
                    raise KeyNotFoundError(f"'{m}' is not a measure of cube '{self._name}'.")
                idx_measure.append(self._measures[m])
        else:
            idx_measure = self._measures[self._default_measure]

        if len(address) != self._dim_count:
            raise ValueError("Invalid number of dimensions in idx_address.")
        idx_address = list(range(0, self._dim_count))
        super_level = 0
        for d in range(0, self._dim_count):
            if address[d] in self._dimensions[d].member_idx_lookup:
                idx_address[d] = self._dimensions[d].member_idx_lookup[address[d]]
                super_level += self._dimensions[d].members[idx_address[d]][self._dimensions[d].LEVEL]
            else:
                raise ValueError(f"'{address[d]}' is not a member of dimension '{self._dimensions[d]._name}'.")
        return tuple(idx_address), super_level, idx_measure

    def _remove_members(self, dimension, members):
        """Removes members from indexes and data table"""
        ordinal = self.get_dimension_ordinal(dimension.name)
        if ordinal == -1:  # dimension is not contained in this cube
            return

        if type(ordinal) is int:
            ordinal = [ordinal]

        # clear fact table
        for o in ordinal:
            self._facts.remove_members(o, members)

    # endregion

    def create_cursor(self, *args) -> Cursor:
        """Create a Cursor for the Cube."""
        return Cursor.create(self, self._dim_lookup, args, self.__to_bolt(args))

    def _create_cursor_from_bolt(self, address, bolt) -> Cursor:
        """Create a Cursor for the Cube directly from an existing bolt."""
        return Cursor.create(self, self._dim_lookup, address, bolt)

    def _get_default_cell_address(self):
        address = []
        for dim in self._dimensions:
            keys = list(dim.member_idx_lookup.keys())
            address.append(keys[0])
        return tuple(address)
