from tinyolap.fact_table import FactTable
from tinyolap.formulas import Formulas

class Cube:
    def __init__(self, name: str, dimensions, measures):
        self.name = name
        self.dim_count = len(dimensions)
        self.dimensions = dimensions
        self.fact_table = FactTable(self.dim_count, self)
        self.measures = {}
        for idx, measure in enumerate(measures):
            self.measures[measure] = idx
        self.aggregations = 0
        self.formulas = Formulas(self)
        self.caching = True
        self.cache = {}

    def caching(self) -> bool:
        """Returns 'True' if caching is activated for the cube, 'False' otherwise.
        By default, caching is activated for all cubes."""
        return self.caching

    def activate_caching(self):
        """Activates caching of aggregated cell values for the cube. Useful for accessing larger cubes.
        The cache will be flushed on every new value written to the cube. Cache warming may need some time."""
        self.caching = True

    def deactivate_caching(self):
        """Deactivates caching of aggregated cell values for the cube. The cache will be flushed instantly."""
        self.caching = False
        self.cache = {}

    def add_formula(self, formula: str) -> (bool, str):
        """Adds a new mathematical formula for measure calculations to the Cube. The methods returns a boolean value
        and string message. If the formula was successfully added to the Cube, then the values <True> and <None>
        will be return, on failure the value <False> and an error message will be returned.
        """
        return self.formulas.add(formula)

    def get_dimension_by_index(self, index:int):
        """Returns the dimension defined for the given dimension index."""
        if (index < 0) or (index > self.dim_count):
            raise ValueError(f"Requested dimension index '{index}' is out of range [{0}, {self.dim_count}].")
        return self.dimensions[index]

    def get_dimension_ordinal(self, name: str):
        """Returns the dimension defined for the given dimension index."""
        for idx, dim_name in enumerate([dim.name for dim in self.dimensions]):
            if name == dim_name:
                return idx
        return -1

    def get_dimension(self, name:str):
        """Returns the dimension defined for the given dimension index."""
        result = [dim for dim in self.dimensions if dim.name == name]
        if not result:
            raise ValueError(f"Requested dimension '{name}' is not a dimension of cube {self.name}.")
        return result[0]

    def get_measures(self):
        return self.measures.keys()

    def get(self, address: tuple, measure=None):
        """Returns a value from the cube for a given address and measure.
        If no records exist for the given address, then 0.0 will be returned."""
        if type(measure) is str:
            idx_address, super_level, idx_measure = self.__validate_address(address, measure)
            if super_level == 0:
                # This is a base-level cell
                # ...direct lookup of value from fact table
                return self.fact_table.get(idx_address, idx_measure)
            else:
                if self.caching:
                    if address in self.cache:
                        return self.cache[address]  # clear the cache

                # This is an aggregated cell
                #  ...check for rules execution first
                if self.formulas:
                    success, result = self.formulas.on_get(super_level, address, measure)
                    if success:
                        if self.caching:
                            self.cache[address] = result  # save value to cache
                        return result

                # ...execute a cell query and aggregate all returned records
                total = 0.0
                for row in self.fact_table.query(idx_address):
                    value = self.fact_table.get_value_by_row(row, idx_measure)
                    if type(value) is float:
                        # This type check allows to store any datatype in the cube and ignore empty cells.
                        total += self.fact_table.get_value_by_row(row, idx_measure)
                    self.aggregations += 1
                if self.caching:
                    self.cache[address] = total  # save value to cache
                return total

        elif not measure:
            return [self.get(address, m) for m in self.measures]
        elif type(measure) is list or type(measure is tuple):
            return [self.get(address, m) for m in measure]
        else:
            raise ValueError(f"Argument type not supported. Argument 'Measure' is of type {type(measure)} "
                             f"but only types 'string', 'list' and 'tuple' or value 'None' are supported.")

    def set(self, address: tuple, measure, value):
        """Writes a value to the cube for the given address and measure."""
        if self.caching:
            self.cache = {}  # clear the cache

        if type(measure) is str:  # single measure
            idx_address, super_level, idx_measure = self.__validate_address(address, measure)
            if super_level == 0:
                # This is a base-level cell
                # ...direct write to fact table
                result = self.fact_table.set(idx_address, idx_measure, value)

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
            if type(value) is list or type(value) is tuple:
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
            if measure not in self.measures:
                raise ValueError(f"'{measure}' is not a measure of cube '{self.name}'.")
            idx_measure = self.measures[measure]
        else:
            idx_measure = None
        if len(address) != self.dim_count:
            raise ValueError("Invalid number of dimensions in address.")
        idx_address = list(range(0, self.dim_count))
        super_level = 0
        for d in range(0, self.dim_count):
            if address[d] in self.dimensions[d].member_idx_lookup:
                idx_address[d] = self.dimensions[d].member_idx_lookup[address[d]]
                super_level += self.dimensions[d].members[idx_address[d]][self.dimensions[d].LEVEL]
            else:
                raise ValueError(f"'{address[d]}' is not a member of dimension '{self.dimensions[d].name}'.")
        return tuple(idx_address), super_level, idx_measure
