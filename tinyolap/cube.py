# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import collections
import collections.abc
# from inspect import isroutine, getsource, getfile, getsourcefile
import inspect
import json
from collections.abc import Iterable

from storage.storageprovider import StorageProvider
from tinyolap.area import Area
from tinyolap.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.cell_context import CellContext
from tinyolap.dimension import Dimension
from tinyolap.exceptions import *
from tinyolap.fact_table import FactTable
from tinyolap.rules import Rules, RuleScope, RuleInjectionStrategy


class Cube:
    """Represents a multi-dimensional table."""
    __magic_key = object()

    @classmethod
    def create(cls, storage_provider: StorageProvider, name: str = None,
               dimensions: list[Dimension] = None, measures: list[str] = None,
               description: str = None):
        cube = Cube(Cube.__magic_key, name, dimensions, measures, description)
        cube._storage_provider = storage_provider
        if name:
            if storage_provider and storage_provider.connected:
                storage_provider.add_cube(name, cube.to_json())
        return cube

    def __init__(self, cub_creation_key, name: str, dimensions=None, measures=None, description: str = None):
        """
        NOT INTENDED FOR DIRECT USE! Cubes and dimensions always need to be managed by a Database.
        Use method 'Database.add_cube(...)' to create objects type Cube.

        :param name: NAme of the cube
        :param dimensions: A list of dimensions that defines the cube axis.
        :param measures: A list if measures.
        :param description: (optional) description for the cube.
        """
        assert (cub_creation_key == Cube.__magic_key), \
            "Objects of type Cube can only be created through the method 'Database.add_cube()'."

        self._name = name
        self._description = description
        self._dim_count = len(dimensions)
        self._dimensions = tuple(dimensions)
        self._dim_names = []
        self._dim_lookup = CaseInsensitiveDict([(dim.name, idx) for idx, dim in enumerate(dimensions)])
        self._facts = FactTable(self._dim_count, self)

        self._database = None
        self._storage_provider: StorageProvider = None

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

        self._cell_request_counter: int = 0
        self._rule_request_counter: int = 0
        self._aggregation_counter: int = 0
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

        :param pattern: The trigger of the rule to be removed.
        :return: ``True``, if a function with the given trigger was found and removed, ``False`` otherwise.
        """
        return NotImplemented

    def remove_all_rules(self):
        """
        Removes all rule functions from the cube.
        """
        return NotImplemented

    def register_rule(self, function, trigger: list[str] = None,
                      scope: RuleScope = None, injection: RuleInjectionStrategy = None):
        """
        Registers a rule function for the cube. Rules function either need to be decorated with the ``@rules(...)``
        decorator or the arguments ``trigger`` and ``scope`` of the ``add_rules(...)`` function must be specified.

        :param function: The rules function to be called.
        :param trigger: The cell idx_address trigger that should trigger the rule.
        :param scope: The scope of the rule.
        """
        offset = 0
        if not inspect.isroutine(function):
            if callable(function) and function.__name__ == "<lambda>":
                offset = 1
            else:
                raise RuleException(
                    f"Argument 'function' does not seem to be a Python function, type id '{type(function)}'.")

        # validate function and decorator parameters
        function_name = str(function).split(" ")[1 + offset]
        cube_name = self.name
        if hasattr(function, "cube"):
            cube_name = function.cube
            if cube_name.lower() != self.name.lower():
                raise RuleException(
                    f"Failed to add rule function. Function '{function_name}' does not seem to be associated "
                    f"with this cube '{self.name}', but with cube '{cube_name}'.")
        if not trigger:
            if hasattr(function, "trigger"):
                trigger = function.pattern
                if type(trigger) is str:
                    trigger = [trigger, ]
                if not type(trigger) is list:
                    raise RuleException(f"Failed to add rule function. Argument 'trigger' is not of the expected "
                                        f"type 'list(str)' but of type '{type(trigger)}'.")
            else:
                raise RuleException(f"Failed to add rule function. Argument 'trigger' missing for "
                                    f"function {function_name}'. Use the '@rule(...) decorator from tinyolap.decorators.")

        if not scope:
            if hasattr(function, "scope"):
                scope = function.scope
                if not (str(type(scope)) == str(type(RuleScope.ROLL_UP))):
                    raise RuleException(f"Failed to add rule function. Argument 'scope' is not of the expected "
                                        f"type ''{type(RuleScope.ALL_LEVELS)}' but of type '{type(scope)}'.")
            else:
                raise RuleException(f"Failed to add rule function. Argument 'scope' missing for "
                                    f"function {function_name}'. Use the '@rule(...) decorator from tinyolap.decorators.")
        if not injection:
            if hasattr(function, "injection"):
                injection = function.injection
            else:
                injection = RuleInjectionStrategy.NO_INJECTION

        if type(trigger) is str:  # a lazy user forgot to put the trigger in brackets
            trigger = [trigger, ]

        idx_pattern = self.__pattern_to_idx_pattern(trigger)

        if scope == RuleScope.ALL_LEVELS:
            self._rules_all_levels.register(function, function_name, trigger, idx_pattern, scope, injection)
        elif scope == RuleScope.AGGREGATION_LEVEL:
            self._rules_aggr_level.register(function, function_name, trigger, idx_pattern, scope, injection)
        elif scope == RuleScope.BASE_LEVEL:
            self._rules_base_level.register(function, function_name, trigger, idx_pattern, scope, injection)
        elif scope == RuleScope.ROLL_UP:
            self._rules_roll_up.register(function, function_name, trigger, idx_pattern, scope, injection)
        elif scope == RuleScope.ON_ENTRY:
            self._rules_on_entry.register(function, function_name, trigger, idx_pattern, scope, injection)
        else:
            raise RuleException(f"Unexpected value '{str(scope)}' for argument 'scope: RuleScope'.")

        # add function to code manager
        self._database._code_manager.register_function(
            function=function, cube=cube_name, trigger=trigger,
            scope=scope, injection=injection)

    def validate_rules(self, save_on_validation: bool = True) -> bool:
        """
        Validates all registered rules by calling each with a random cell matching the defined
        rule trigger and rule scope. Calling this methods (maybe even multiple times) can be
        usefull for highlevel testing of your rules.

        .. warning::
            Calling this method does not replace proper rule testing. Escpecially when your
            database should be used by other users or for serious purposes you need to ensure
            that your rule calculations ideally never (or only for explicit purposes) thows an
            error.

        :return: ``True`` if all rules returned a result with throwing an error.
        """
        # todo: to be implemented

        # update the database
        self._database.save()
        return True

    def __pattern_to_idx_pattern(self, pattern):
        """
        Converts a trigger into it's index representation.

        :param pattern: The trigger to be converted.
        :return: The index trigger.
        """
        if type(pattern) is str:
            pattern = list((pattern,))
        # Sorry, miss-use of cursor. maybe some refactoring required...
        address = self._get_default_cell_address()
        c = self._create_cell_from_bolt(address, self._address_to_bolt(address))
        # create something like this: idx_pattern = [(0, 3)]
        idx_pattern = []
        for p in pattern:
            idx_dim, idx_member, member_level = c._get_member(p)
            idx_pattern.append((idx_dim, idx_member))
        return idx_pattern

    # endregion

    # region Properties
    @property
    def cells_count(self) -> int:
        return len(self._facts.facts)

    @property
    def name(self) -> str:
        """Returns the name of the cube."""
        return self._name

    @property
    def counter_cell_requests(self) -> int:
        """Returns the number of cell requests executed."""
        return self._cell_request_counter

    @property
    def counter_rule_requests(self) -> int:
        """Returns the number of rules that have been executed."""
        return self._rule_request_counter

    @property
    def counter_aggregations(self) -> int:
        """Returns the number aggregations that have been executed."""
        return self._aggregation_counter

    def reset_counters(self):
        """Resets the internal counters for cell- and rule-requests and aggregations."""
        self._cell_request_counter = 0
        self._rule_request_counter = 0
        self._aggregation_counter = 0

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

    # region CellContext access via indexing/slicing
    def __getitem__(self, item):
        bolt = self._address_to_bolt(item)
        return self._get(bolt)

    def __setitem__(self, item, value):
        bolt = self._address_to_bolt(item)
        self._set(bolt, value)

    def __delitem__(self, item):
        bolt = self._address_to_bolt(item)
        self._set(bolt, None)

    # endregion

    # region Read and write values
    def clear(self):
        """
        Removes all values from the Cube.
        """
        self._facts.clear()

    def get(self, address: tuple):
        """Reads a value from the cube for a given idx_address.
        If no records exist for the given idx_address, then 0.0 will be returned.
        :raises InvalidKeyException:
        """
        bolt = self._address_to_bolt(address)
        return self._get(bolt)

    def set(self, address: tuple, value):
        """Writes a value to the cube for the given bolt (idx_address and measures)."""
        bolt = self._address_to_bolt(address)
        return self._set(bolt, value)

    def _get(self, bolt, bypass_rules=False):
        """
        Returns a value from the cube for a given idx_address and measure.
        If no records exist for the given idx_address, then 0.0 will be returned.
        """
        (super_level, idx_address, idx_measures) = bolt
        self._cell_request_counter += 1

        # caching
        if not bypass_rules:
            if self._caching and bolt in self._cache:
                return self._cache[bolt]

        # ALL_LEVELS rules
        if not bypass_rules:
            if self._rules_all_levels.any:
                found, func = self._rules_all_levels.first_match(idx_address)
                if found:
                    cursor = self._create_cell_from_bolt(None, (super_level, idx_address, idx_measures))
                    try:
                        self._rule_request_counter += 1
                        value = func(cursor)
                        if value != CellContext.CONTINUE:
                            if self._caching:
                                self._cache[bolt] = value  # save value to cache
                            return value
                    except Exception as e:
                        return "ERR"
                        raise RuleException(f"Rule function {func.__name__} failed. {str(e)}")

        if super_level == 0:  # base-level cells
            # BASE_LEVEL rules
            if not bypass_rules:
                if self._rules_base_level.any:
                    found, func = self._rules_base_level.first_match(idx_address)
                    if found:
                        cursor = self._create_cell_from_bolt(None, (super_level, idx_address, idx_measures))
                        try:
                            self._rule_request_counter += 1
                            value = func(cursor)
                            if value != CellContext.CONTINUE:
                                if self._caching:
                                    self._cache[bolt] = value  # save value to cache
                                return value
                        except Exception as e:
                            raise RuleException(f"Rule function {func.__name__} failed. {str(e)}")

            if type(idx_measures) is int:
                return self._facts.get(idx_address, idx_measures)
            else:
                raise FatalException("Depreciated. Feature Needs to be removed")
                # self._cell_request_counter += len(idx_measures)
                # return [self._facts.get(idx_address, m) for m in idx_measures]

        else:  # aggregated cells
            # if self._caching and bolt in self._cache:
            #     self._cell_request_counter += 1
            #     return self._cache[bolt]

            # AGGREGATION_LEVEL
            if not bypass_rules:
                if self._rules_aggr_level.any:
                    found, func = self._rules_aggr_level.first_match(idx_address)
                    if found:
                        cursor = self._create_cell_from_bolt(None, (super_level, idx_address, idx_measures))
                        try:
                            self._rule_request_counter += 1
                            value = func(cursor)
                            if value != CellContext.CONTINUE:
                                if self._caching:
                                    self._cache[bolt] = value  # save value to cache
                                return value
                        except Exception as e:
                            raise RuleException(f"Rule function {func.__name__} failed. {str(e)}")

            # get records row ids for current cell idx_address
            rows = self._facts.query(idx_address)
            self._aggregation_counter += len(rows)

            # aggregate records
            if type(idx_measures) is int:
                if not rows:
                    return 0.0
                facts = self._facts.facts
                total = 0.0

                # todo: add support for ROLL_UP rules

                for row in rows:
                    if idx_measures in facts[row]:
                        value = facts[row][idx_measures]
                        if type(value) is float:
                            total += value

                if self._caching:
                    self._cache[bolt] = total  # save value to cache

                return total
            else:
                raise FatalException("Depreciated. Feature Needs to be removed")
                # if not rows:
                #     return [0.0] * len(idx_measures)
                # facts = self._facts.facts
                # totals = [] * len(idx_measures)
                # for idx, idx_m in idx_measures:
                #     for row in rows:
                #         if idx_m in facts[row]:
                #             value = facts[row][idx_m]
                #             if type(value) is float:
                #                 totals[idx] += value
                #
                # if self._caching:
                #     self._cache[bolt] = totals  # save value to cache
                # return totals

    def _set_base_level_cell(self, idx_address, idx_measure, value):
        """Writes a base level value to the cube for the given idx_address (idx_address and measures)."""
        self._facts.set(idx_address, idx_measure, value)
        if self._storage_provider and self._storage_provider.connected:
            if value:
                self._storage_provider.set_record(self._name, str(idx_address), json.dumps({"v": value}))
            else:
                self._storage_provider.set_record(self._name, str(idx_address))

    def _set(self, bolt, value):
        """Writes a value to the cube for the given bolt (idx_address and measures)."""
        if self._caching and self._cache:
            self._cache = {}  # clear the cache

        (super_level, idx_address, idx_measures) = bolt

        if type(value) is int:
            value = float(value)

        if super_level == 0:  # for base-level cells...
            if type(idx_measures) is int:
                result = self._facts.set(idx_address, idx_measures, value)
                if self._storage_provider and self._storage_provider.connected:
                    if value:
                        self._storage_provider.set_record(self._name, str(idx_address), json.dumps({"v": value}))
                    else:
                        self._storage_provider.set_record(self._name, str(idx_address))

            # todo: rework or remove measures
            elif isinstance(idx_measures, collections.abc.Sequence):
                if isinstance(value, collections.abc.Sequence):
                    if len(idx_measures) != len(value):
                        raise InvalidKeyException(f"Arguments for write back not aligned. The numbers of measures "
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
            raise InvalidOperationException(f"Write back to aggregated cells in not (yet) supported.")

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
            if address[d] in self._dimensions[d]._member_idx_lookup:
                idx_address[d] = self._dimensions[d]._member_idx_lookup[address[d]]
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

    def _idx_address_to_address(self, idx_address, include_cube_name: bool = False):
        """
        Converts an idx_address index to a idx_address with member names
        :param idx_address:
        :return:
        """
        if include_cube_name:
            address = [self.name, ]
        else:
            address = []
        for i in range(self._dim_count):
            address.append(self._dimensions[i].members[idx_address[i]][1])
        return address

    def _address_to_idx_address(self, address):
        """
        Converts an address to an idx_address index with member ids.
        :param idx_address:
        :return:
        """
        bolt = self._address_to_bolt(address)
        return bolt[1]

    def _address_to_bolt(self, address):
        """Converts a given address, incl. member and (optional) measures, into a bolt.
        A bolt is a tuple of integer address, used for internal access of cells.
        """

        dim_count = self._dim_count
        measures_count = len(address) - dim_count
        if measures_count < 0:
            raise InvalidCellAddressException(f"Invalid idx_address. At least {self._dim_count} members expected "
                                              f"for cube '{self._name}, but only {len(address)} where passed in.")
        # Validate members
        dimensions = self._dimensions
        idx_address = [None] * dim_count
        super_level = 0
        for i, member in enumerate(address[: dim_count]):
            if member in dimensions[i]._member_idx_lookup:
                idx_address[i] = dimensions[i]._member_idx_lookup[member]
                super_level += dimensions[i].members[idx_address[i]][6]
            else:
                raise InvalidCellAddressException(f"Invalid idx_address. '{member}' is not a member of the {i}. "
                                                  f"dimension '{dimensions[i].name}' in cube {self._name}.")
        idx_address = tuple(idx_address)

        # validate measures (if defined)
        if measures_count == 0:
            idx_measures = self._measures[self._default_measure]
        else:
            idx_measures = []
            for measure in address[self._dim_count:]:
                if measure not in self._measures:
                    raise InvalidCellAddressException(f"'{measure}' is not a measure of cube '{self.name}'.")
                idx_measures.append(self._measures[measure])
            if measures_count == 1:
                idx_measures = idx_measures[0]
            else:
                idx_measures = tuple(idx_measures)

        return super_level, idx_address, idx_measures  # that's the 'bolt'

    # endregion

    # region cells
    def cell(self, *args) -> CellContext:
        """Returns a new CellContext from the Cube."""
        return CellContext.create(self, self._dim_lookup, args, self._address_to_bolt(args))

    def _create_cell_from_bolt(self, address, bolt) -> CellContext:
        """Create a CellContext for the Cube directly from an existing bolt."""
        return CellContext.create(self, self._dim_lookup, address, bolt)

    def _get_default_cell_address(self):
        """Generates a default address. This is the first member from all dimensions."""
        address = []
        for dim in self._dimensions:
            # keys = list(dim._member_idx_lookup.keys())
            # address.append(keys[0])
            address.append(dim.get_first_member())
        return tuple(address)

    def _get_records(self):
        """
        Returns all records and values from the cube as a list[tuple[address:str, value_as_json:str].
        Useful for database serialization.
        """
        records = []
        for address, data in zip(self._facts.addresses, self._facts.facts):
            records.append((str(address), json.dumps(data)))
        return records

    # endregion

    # region serialization
    # todo: adjust to fully support cube (e.g. rules)
    def to_json(self):
        """
        Returns the json representation of the cube. Helpful for serialization
        and deserialization of cubes. The json returned by this function is
        the same as the one used by storage providers (if available).

        :param beautify: Identifies if the json code should be beautified (multiple rows + indentation).
        :return: A json string representing the cube.
        """
        dim_names = [dim.name for dim in self._dimensions]
        rules_count = len(self._rules_roll_up) + len(self._rules_on_entry) \
                      + len(self._rules_all_levels) + len(self._rules_base_level) + len(self._rules_aggr_level)
        config = {"content": "cube",
                  "name": self.name,
                  "description": self._description,
                  "dimensions": dim_names,
                  "caching": self._caching,
                  "rules": rules_count,
                  }

        json_string = json.dumps(config, indent=4)
        return json_string

    # todo: adjust to fully support cube (e.g. rules)
    def from_json(self, json_string: str):
        """
        Initializes the cube from a json string.

        .. warning::
            Calling this method for cubes which are already in use (contain data)
            will very likely **corrupt your database!** Calling this method is only save
            **before** you write any data to a cube. Handle with care.

        :param json_string: The json string containing the cube definition.
        :raises FatalException: Raised if an error occurred during the deserialization from json string.
        """
        try:
            # read configuration
            config = json.loads(json_string)
            self._name  = config["name"]
            self._description = config["description"]
            new_dim_names = config["dimensions"]
            self._dimensions = tuple([self._database.dimension[dim_name] for dim_name in new_dim_names])
            self._caching = config["caching"]

            # load data
            if self._storage_provider:
                records = self._storage_provider.get_records(self._name)
                for record in records:
                    address = str(record[0])
                    idx_address = list(map(int, address[1:-1].split(sep=",")))

                    data = json.loads(record[1])
                    for key, value in data.items:
                        idx_measure = self._measures[key]
                        self._set_base_level_cell(idx_address, idx_measure, value)

            # initialize rules
            # Note: This should to be done after loading the data, as otherwise push rules
            #       might be triggered and recalcluated although the data is already consistent.
            if config["rules"] > 0:
                functions = self._database._code_manager.get_functions(self._name)
                for f in functions:
                    self.register_rule(function=f.function, trigger=f.trigger, scope= f.scope, injection=f.injection)



        except Exception as err:
            raise FatalException(f"Failed to load json for dimension '{self.name}'. {str(err)}")

    # endregion

    # region areas
    def area(self, *args) -> Area:
        """Returns a new Area fom the Cube."""
        return Area(self, args)

    # endregion
