from __future__ import annotations
from collections.abc import Iterable, Sized
from exceptions import *
from dimension import Dimension
from formulas import Formulas


class Cube:
    __magic_key = object()

    @classmethod
    def create(cls, backend, name: str, dimensions: list[Dimension], measures: list[str]):
        cube = Cube(Cube.__magic_key, name, dimensions, measures)
        cube._backend = backend
        cube._backend_table = backend.add_cube(name, dimensions, cube.measures.values())
        return cube

    """Represents a multi-dimensional table."""
    def __init__(self, create_key,  name: str, dimensions: list[Dimension], measures: list[str]):
        """
        NOT INTENDED FOR DIRECT USE! Use method 'Database.add_cube(...)' to create Cube objects.
        :param name:
        :param dimensions:
        :param measures:
        """
        assert(create_key == Cube.__magic_key), \
            "Objects of type Cube can only be created through the Database.add_cube() method."

        self._name = name
        self._dim_count = len(dimensions)
        self.dimensions = dimensions
        self.measures = {}
        for idx, measure in enumerate(measures):
            self.measures[measure] = idx
        self._aggregations = 0
        self.formulas = Formulas(self)
        self._backend = None
        self._backend_table = None
        self._caching = True
        self._cache = {}

    # region Properties
    @property
    def name(self) -> str:
        """Returns the name of the cube."""
        return self._name

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
        return len(self.measures)
    # endregion

    # region Cube Formulas and Constraints
    def add_formula(self, formula: str) -> (bool, str):
        """Adds a new mathematical formula for measure calculations to the Cube. The methods returns a boolean value
        and string message. If the formula was successfully added to the Cube, then the values <True> and <None>
        will be return, on failure the value <False> and an error message will be returned.
        """
        return self.formulas.add(formula)
    # endregion

    # region Dimension and Measures related methods
    def get_dimension_by_index(self, index: int):
        """Returns the dimension defined for the given dimension index."""
        if (index < 0) or (index > self._dim_count):
            raise ValueError(f"Requested dimension index '{index}' is out of range [{0}, {self._dim_count}].")
        return self.dimensions[index]

    def get_dimension_ordinal(self, name: str):
        """Returns the dimension defined for the given dimension index."""
        for idx, dim_name in enumerate([dim._name for dim in self.dimensions]):
            if name == dim_name:
                return idx
        return -1

    def get_dimension(self, name: str):
        """Returns the dimension defined for the given dimension index."""
        result = [dim for dim in self.dimensions if dim._name == name]
        if not result:
            raise ValueError(f"Requested dimension '{name}' is not a dimension of cube {self._name}.")
        return result[0]

    def get_measures(self):
        return self.measures.keys()
    # endregion

    # region Cell access by Address Indexing
    def __getitem__(self, item):
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
        self.set(address, measures, None)
    # endregion

    # region Cell access (read/write values)
    def get(self, address: tuple, measures=None):
        """Returns a value from the cube for a given address and measure.
        If no records exist for the given address, then 0.0 will be returned."""

        # validate address and measures
        if not measures:
            measures = self.measures.keys()
        elif type(measures) is str:
            measures = [measures]
        elif not isinstance(measures, Iterable):
            raise InvalidKeyException(f"Invalid measures '{str(measures)}, string or list of string expected.")
        idx_address, super_level, idx_measure = self.__validate_address(address, measures)

        if super_level == 0:
            # This is a base-level cell
            # ...direct lookup of value from fact table
            return self._backend.cube_get(self._name, idx_address, idx_measure)
        else:
            if self._caching:
                if address in self._cache:
                    return self._cache[address]

            # This is an aggregated cell
            #  ...check for rules execution first
            if self.formulas:
                success, result = self.formulas.on_get(super_level, address, measures)
                if success:
                    if self._caching:
                        self._cache[address] = result  # save value to cache
                    return result

            # ...prepare and execute a range query, aggregating all returned records
            range_address = self._range_from_address(idx_address)
            records = self._backend.cube_get_range(self._name, range_address, idx_measure, aggregate=True)
            if records:
                value = records[0][0]
                if value is None:
                    return 0.0
                else:
                    return value
            else:
                return 0.0

    def set(self, address: tuple, measure, value):
        """Writes a value to the cube for the given address and measure."""
        if self._caching:
            if self._cache:
                self._cache = {}  # clear the cache

        if type(measure) is str:  # single measure
            idx_address, super_level, idx_measure = self.__validate_address(address, measure)
            if super_level == 0:
                # This is a base-level cell
                # ...direct write to fact table
                result = self._backend.cube_set(self._name, idx_address, idx_measure, value)

                #  ...check for base-level (push) rules to be execution first
                if self.formulas:
                    success = self.formulas.on_set(super_level, address, measure, value)
                    if success:
                        return success

                return result

            else:
                # This is an aggregated cell
                # ...write back to aggregated cells not yet provided (splashing)
                raise ValueError(f"Write back on aggregated cells is not yet supported.")
        elif type(measure) is list or type(measure) is tuple:
            if not (type(value) is list or type(value) is tuple):
                value = (value,) * len(measure)

            if len(value) == len(measure):
                result = True
                for m, v in zip(measure, value):
                    result &= self.set(address, m, v)
                return result
            raise ValueError(f"Arguments not aligned. Arguments 'measure' and 'value' needs both to be a list or tuple"
                             f" of same length.")
        elif not measure:
            if type(value) is list or type(value) is tuple:
                if len(value) < len(self.measures):
                    result = True
                    for m, v in zip(self.measures, value):
                        result &= self.set(address, m, v)
                    return result
            raise ValueError(f"Argument type not supported. Argument 'Value' needs to be a list or tuple"
                             f" of length {len(self.measures)} or less.")
        else:
            raise ValueError(f"Argument type not supported. Argument 'Measure' is of type {type(measure)} "
                             f"but only 'string', 'list' and 'tuple' are supported.")
    # endregion

    # region internal methods
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

    def __validate_address(self, address: tuple, measures):
        """Validates a given address and measures and returns the according indexes."""
        if type(measures) is str:
            if measures not in self.measures:
                raise ValueError(f"'{measures}' is not a measure of cube '{self._name}'.")
            idx_measure = [self.measures[measures]]
        elif isinstance(measures, Iterable):
            idx_measure = []
            for measure in measures:
                if measure not in self.measures.keys():
                    raise KeyNotFoundException(f"'{measure}' is not a measure of cube '{self._name}'.")
                idx_measure.append(self.measures[measure])
        else:
            idx_measure = None

        if len(address) != self._dim_count:
            raise ValueError("Invalid number of dimensions in address.")
        idx_address = list(range(0, self._dim_count))
        super_level = 0
        for d in range(0, self._dim_count):
            if address[d] in self.dimensions[d].member_idx_lookup:
                idx_address[d] = self.dimensions[d].member_idx_lookup[address[d]]
                super_level += self.dimensions[d].members[idx_address[d]][self.dimensions[d].LEVEL]
            else:
                raise ValueError(f"'{address[d]}' is not a member of dimension '{self.dimensions[d].name}'.")
        return tuple(idx_address), super_level, idx_measure

    def __remove_members(self, dimension, members):
        """Remove data for obsolete (deleted) members within cubes.
        Formulas containing that member will get invalidated."""

        # check if the dimension is in use for this cube.
        if dimension not in self.dimensions:
            return

        for cube in self.cubes:
            cube.__remove_members(dimension, members)
        # todo: Invalidate rules containing obsolete members.
        pass

    def _range_from_address(self, idx_address):
        """Returns a range query from an aggregated address
        by resolving all the base-level children for that address."""
        range_from_address = []
        for idx, dim in zip(idx_address, self.dimensions):
            if dim.members[idx][dim.LEVEL] == 0:
                # base level member
                base_members = [idx]
            else:
                # aggregated member
                base_members = dim.members[idx][dim.BASE_CHILDREN]
            range_from_address.append(base_members)
        return range_from_address

    # endregion
