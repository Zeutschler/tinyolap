import collections
from collections.abc import Iterable, Sized

from tinyolap.custom_exceptions import *
from tinyolap.fact_table import FactTable
from tinyolap.rules import Rules
from tinyolap.dimension import Dimension

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
        self.dimensions = dimensions
        self._fact_table = FactTable(self._dim_count, self)
        self._alias = {}
        self._has_alias: bool = False

        if not measures:
            measures = ["value"]  # create a default measure if none is defined
        self._measures = {}
        for idx, measure in enumerate(measures):
            self._measures[measure] = idx
        self._default_measure = measures[0]

        self._cell_requests = 0
        self._rules = Rules(self)
        self._caching = True
        self._cache = {}

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
            raise KeyNotFoundException(f"Failed to set default member. "
                                       f"'{value}' is not a measure of cube '{self._name}'.")
        self._default_measure = value

    @property
    def measures(self) -> list[str]:
        """Returns the list of measures of a cube."""
        return [str(self._measures.keys())]

    # endregion

    # region Cube Formulas and Constraints
    def add_formula(self, formula: str) -> (bool, str):
        """Adds a new mathematical formula for measure calculations to the Cube. The methods returns a boolean value
        and string message. If the formula was successfully added to the Cube, then the values <True> and <None>
        will be return, on failure the value <False> and an error message will be returned.
        """
        return self._rules.add(formula)

    # endregion

    # region Dimension and Measures related methods
    def get_measures(self) -> list[str]:
        """Returns the list of measures of a cube."""
        return list(self._measures.keys())

    def get_dimension_by_index(self, index: int):
        """Returns a dimension from a cubes list of dimensions at the given index."""
        if (index < 0) or (index > self._dim_count):
            raise ValueError(f"Requested dimension index '{index}' is out of range [{0}, {self._dim_count}].")
        return self.dimensions[index]

    def get_dimension_ordinal(self, name: str):
        """Returns the dimension defined for the given dimension index."""
        for idx, dim_name in enumerate([dim.name for dim in self.dimensions]):
            if name == dim_name:
                return idx
        return -1

    def get_dimension(self, name: str):
        """Returns the dimension defined for the given dimension index."""
        result = [dim for dim in self.dimensions if dim.name == name]
        if not result:
            raise ValueError(f"Requested dimension '{name}' is not a dimension of cube {self.name}.")
        return result[0]

    # endregion

    # region Cell access via indexing
    def __getitem__(self, item):
        bolt = self.__to_bolt(item)
        return self.__get(bolt)

    def __getitem_old__(self, item):
        if isinstance(item, Sized):
            if len(item) < self._dim_count:
                raise InvalidKeyException(f"Invalid cube cell index, at least {self._dim_count} index items "
                                          f"expected, but only {len(item)} found.")
            address = tuple(item[:self._dim_count])
            measures = tuple(item[self._dim_count:])
        elif type(item) is str:
            address = tuple(item)
            measures = ()
        else:
            raise InvalidKeyException(f"Invalid cube cell index '{str(item)}.")
        return self.get(address, measures)

    def __setitem__(self, item, value):
        bolt = self.__to_bolt(item)
        self.__set(bolt, value)

    def __setitem_old__(self, item, value):
        if isinstance(item, Sized):
            if len(item) < self._dim_count:
                raise InvalidKeyException(f"Invalid cube cell index, at least {self._dim_count} index items "
                                          f"expected, but only {len(item)} found.")
            address = tuple(item[:self._dim_count])
            measures = tuple(item[self._dim_count:])
        elif type(item) is str:
            address = tuple(item)
            measures = ()
        else:
            raise InvalidKeyException(f"Invalid cube cell index '{str(item)}.")
        self.set(address, measures, value)

    def __delitem__(self, item):
        bolt = self.__to_bolt(item)
        self.__set(bolt, None)

    # endregion

    # region Read and write values

    # FOR FUTURE USE...
    # def get_value_by_bolt(self, bolt: tuple):
    #     """Returns a value from the cube for a given address and measure.
    #     If no records exist for the given address, then 0.0 will be returned."""
    #     return self.__get(bolt)
    # def get_bolt(self, *keys:str):
    #     return self.__to_bolt(keys)

    def __to_bolt(self, keys):
        """Converts a given address, incl. member and (optional) measures, into a bolt.
        A bolt is a tuple of integer keys, used for internal access of cells.
        """

        dim_count = self._dim_count
        measures_count = len(keys) - dim_count
        if measures_count < 0:
            raise InvalidKeyException(f"Invalid address. At least {self._dim_count} members expected "
                                      f"for cube '{self._name}, but only {len(keys)} where passed in.")
        # Validate members
        idx_address = [None] * dim_count
        super_level = 0
        for i, member in enumerate(keys[: dim_count]):
            if member in self.dimensions[i].member_idx_lookup:
                idx_address[i] = self.dimensions[i].member_idx_lookup[member]
                super_level += self.dimensions[i].members[idx_address[i]][self.dimensions[i].LEVEL]
            else:
                raise ValueError(f"Invalid address. '{member}' is not a member of the {i}. "
                                 f"dimension '{self.dimensions[i].name}' in cube {self._name}.")
        idx_address = tuple(idx_address)

        # validate measures (if defined)
        if measures_count == 0:
            idx_measures = self._measures[self._default_measure]
        else:
            idx_measures = []
            for measure in keys[self._dim_count:]:
                if measure not in self._measures:
                    raise ValueError(f"'{measure}' is not a measure of cube '{self.name}'.")
                idx_measures.append(self._measures[measure])
            if measures_count == 1:
                idx_measures = idx_measures[0]
            else:
                idx_measures = tuple(idx_measures)

        return super_level, idx_address, idx_measures  # that's the 'bolt'

    def get(self, address: tuple):
        """Reads a value from the cube for a given address.
        If no records exist for the given address, then 0.0 will be returned.
        :raises InvalidKeyException:
        """
        bolt = self.__to_bolt(address)
        return self.__get(bolt)

    def set(self, address: tuple, value):
        """Writes a value to the cube for the given bolt (address and measures)."""
        bolt = self.__to_bolt(address)
        return self.__set(bolt, value)

    def __get(self, bolt):
        """Returns a value from the cube for a given address and measure.
        If no records exist for the given address, then 0.0 will be returned."""

        (super_level, idx_address, idx_measures) = bolt
        if super_level == 0:  # base-level cells
            # todo: add Rules lookup
            if type(idx_measures) is int:
                self._cell_requests += 1
                return self._fact_table.get(idx_address, idx_measures)
            else:
                self._cell_requests += len(idx_measures)
                return [self._fact_table.get(idx_address, m) for m in idx_measures]

        else:  # aggregated cells
            if self._caching and bolt in self._cache:
                self._cell_requests += 1
                return self._cache[bolt]

            if self._rules:
                success, result = self._rules.on_get(super_level, idx_address, idx_measures)
                if success:
                    if self._caching:
                        self._cache[bolt] = result
                    return result

            # get records row ids for current cell address
            rows = self._fact_table.query(idx_address)

            # aggregate records
            f_get_value = self._fact_table.get_value_by_row  # make the call local
            if type(idx_measures) is int:
                if not rows:
                    return 0.0
                total = 0.0
                for row in rows:
                    value = f_get_value(row, idx_measures)
                    if type(value) is float:
                        total += value

                self._cell_requests += len(rows)
                if self._caching:
                    self._cache[bolt] = total  # save value to cache

                return total
            else:
                if not rows:
                    return [0.0] * len(idx_measures)
                totals = [] * len(idx_measures)
                for idx, idx_m in idx_measures:
                    for row in rows:
                        value = f_get_value(row, idx_m)
                        if type(value) is float:
                            # This type check allows to store any datatype in the cube and ignore empty cells.
                            totals[idx] += value
                self._cell_requests += len(rows) * len(idx_measures)
                if self._caching:
                    self._cache[bolt] = totals  # save value to cache
                return totals

    def __set(self, bolt, value):
        """Writes a value to the cube for the given bolt (address and measures)."""
        if self._caching and self._cache:
            self._cache = {}  # clear the cache

        (super_level, idx_address, idx_measures) = bolt

        if super_level == 0:  # for base-level cells...
            if type(idx_measures) is int:
                result = self._fact_table.set(idx_address, idx_measures, value)
            elif isinstance(idx_measures, collections.abc.Sequence):
                if isinstance(value, collections.abc.Sequence):
                    if len(idx_measures) != len(value):
                        raise InvalidKeyException(f"Arguments for write back not aligned. The numbers of measures "
                                                  f"and the numbers of values handed in need to be identical.")
                    result = all([self._fact_table.set(idx_address, m, v) for m, v in zip(idx_measures, value)])
                else:
                    result = all([self._fact_table.set(idx_address, m, value) for m in idx_measures])

            #  ...check for base-level (push) rules to be executed
            if self._rules:
                success = self._rules.on_set(super_level, idx_address, idx_measures, value)
                if success:
                    return success

            return result
        else:
            raise InvalidOperationException(f"Write back to aggregated cells in not (yet) supported.")

    def _update_aggregation_index(self, fact_table_index, address, row):
        """Updates all fact table index for all aggregations over all dimensions. FOR INTERNAL USE ONLY!"""
        # please note that a '__' name prefix is not possible
        # as this function is called through a weak reference.
        for d, idx_member in enumerate(address):
            for idx_parent in self.dimensions[d].members[address[d]][self.dimensions[d].ALL_PARENTS]:
                if idx_parent in fact_table_index.index[d]:
                    fact_table_index.index[d][idx_parent].add(row)
                else:
                    fact_table_index.index[d][idx_parent] = {row}

    def __validate_address(self, address: tuple, measure):
        """Validates a given address and measures and return the according indexes."""
        if type(measure) is str:
            if measure not in self._measures:
                raise ValueError(f"'{measure}' is not a measure of cube '{self.name}'.")
            idx_measure = self._measures[measure]
        elif isinstance(measure, Iterable):
            idx_measure = []
            for m in measure:
                if m not in self._measures.keys():
                    raise KeyNotFoundException(f"'{m}' is not a measure of cube '{self._name}'.")
                idx_measure.append(self._measures[m])
        else:
            idx_measure = self._measures[self._default_measure]


        if len(address) != self._dim_count:
            raise ValueError("Invalid number of dimensions in address.")
        idx_address = list(range(0, self._dim_count))
        super_level = 0
        for d in range(0, self._dim_count):
            if address[d] in self.dimensions[d].member_idx_lookup:
                idx_address[d] = self.dimensions[d].member_idx_lookup[address[d]]
                super_level += self.dimensions[d].members[idx_address[d]][self.dimensions[d].LEVEL]
            else:
                raise ValueError(f"'{address[d]}' is not a member of dimension '{self.dimensions[d]._name}'.")
        return tuple(idx_address), super_level, idx_measure

    # endregion
