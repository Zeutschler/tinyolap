# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import inspect
import json
from collections.abc import Iterable

from tinyolap.area import Area
from tinyolap.utilities.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.cell import Cell
from tinyolap.dimension import Dimension
from tinyolap.member import Member
from tinyolap.exceptions import *
from tinyolap.facttable import FactTable
from tinyolap.rules import Rule, Rules, RuleError, RuleScope, RuleInjectionStrategy
from tinyolap.storage.storageprovider import StorageProvider


class CubeWeightManager:
    """Manages weights for aggregations of base level members."""
    def __init__(self, cube: Cube, refresh: bool = False):
        self.is_weighted_cube = False
        self.cube = cube
        self.dim_count = cube.dimensions_count
        self.weighted_dim_idx: tuple[int] = tuple()
        self.dim_weights = [None] * self.dim_count
        if refresh:
            self.refresh()

    def get_weighting(self, address: tuple[int]):
        is_weighted_address = False
        lookups = None
        address_weighted_dim_idx = None
        for idx in self.weighted_dim_idx:
            lookup = self.dim_weights[idx].get(address[idx], False)
            if lookup:
                if not lookups:
                    lookups = [None] * self.dim_count
                    address_weighted_dim_idx = []

                address_weighted_dim_idx.append(idx)
                lookups[idx] = lookup
                is_weighted_address = True

        return is_weighted_address, address_weighted_dim_idx, lookups

    def refresh(self):
        """Refreshes the weight manager based on one or all dimensions of the associated cube."""
        self.is_weighted_cube = False
        dim_idx = []
        for idx, dimension in enumerate(self.cube.dimensions):
            if dimension.is_weighted:
                self.is_weighted_cube = True
                dim_idx.append(idx)
                self.dim_weights[idx] = dimension._weights.weight_lookup
        self.weighted_dim_idx = dim_idx


class Cube:
    """Represents a multi-dimensional table."""
    __magic_key = object()

    @classmethod
    def create(cls, storage_provider: StorageProvider, name: str = None,
               dimensions: list[Dimension] = None,
               description: str = None):
        cube = Cube(Cube.__magic_key, name, dimensions, description)
        cube._storage_provider = storage_provider
        if name and dimensions:
            if storage_provider and storage_provider.connected:
                storage_provider.add_cube(name, cube.to_json())
        return cube

    def __init__(self, cub_creation_key, name: str, dimensions=None, description: str = ""):
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

        cube_creation_from_json = bool(dimensions)

        self._name = name
        self._description = description
        if cube_creation_from_json:
            self._dim_count = len(dimensions)
            self._dimensions = tuple(dimensions)
        else:
            self._dim_count = 0
            self._dimensions = tuple()

        self._names = []
        self._dim_lookup = CaseInsensitiveDict([(dim.name, idx) for idx, dim in enumerate(self._dimensions)])
        self._facts = FactTable(self._dim_count, self)

        self._database = None
        self._storage_provider: StorageProvider  # = None

        self._has_rules: bool = False
        self._rules = Rules(self._name)

        self._cache_hit_counter: int = 0
        self._cell_request_counter: int = 0
        self._rule_request_counter: int = 0
        self._aggregation_counter: int = 0
        self._weighted_aggregation_counter: int = 0
        self._caching = True
        self._cache = {}

        self._weights = CubeWeightManager(self)
        self._weights.refresh()

    def __str__(self):
        return f"cube '{self.name}'"

    def __repr__(self):
        return f"cube '{self.name}'"

    # region areas
    def area(self, *args) -> Area:
        """Create a new data area for the Cube."""
        return Area(self, args)
    # endregion

    # region Properties
    @property
    def cells_count(self) -> int:
        return len(self._facts.facts)

    @property
    def database(self):
        """Returns the database the cube belongs to."""
        return self._database

    @property
    def name(self) -> str:
        """Returns the name of the cube."""
        return self._name

    @property
    def description(self) -> str:
        """Returns the description of the cube."""
        return self._description

    @description.setter
    def description(self, value: str):
        """Sets the description of the cube."""
        self._description = value

    @property
    def rules(self) -> Rules:
        """Returns the rules of the sube."""
        return self._rules

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
        """Returns the number of overall aggregations that have been executed."""
        return self._aggregation_counter

    @property
    def counter_weighted_aggregations(self) -> int:
        """Returns the number weighted aggregations that have been executed."""
        return self._weighted_aggregation_counter

    @property
    def counter_cache_hits(self) -> int:
        """Returns the number cache hits that have occurred."""
        return self._cache_hit_counter



    def reset_counters(self):
        """Resets the internal counters for cell- and rule-requests and aggregations."""
        self._cell_request_counter = 0
        self._rule_request_counter = 0
        self._aggregation_counter = 0
        self._weighted_aggregation_counter = 0
        self._cache_hit_counter = 0

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
    def dimensions(self) -> tuple[Dimension]:
        """Returns the dimensions of the cube."""
        return self._dimensions

    @property
    def dimension_names(self) -> tuple:
        """Returns the number of dimensions of the cube."""
        return tuple(dim.name for dim in self._dimensions)

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
        if len(item) == self._dim_count:
            bolt = self._address_to_bolt(item)
            return self._get(bolt)
        else:
            return self.area(item)

    def __setitem__(self, item, value):
        if len(item) == self._dim_count:
            bolt = self._address_to_bolt(item)
            self._set(bolt, value)
        else:
            self.area(item).set_value(value)

    def __delitem__(self, item):
        if len(item) == self._dim_count:
            bolt = self._address_to_bolt(item)
            self._set(bolt, None)
        else:
            self.area(item).clear()

    # endregion

    # region Read and write values
    def clear(self):
        """
        Removes all values from the Cube.
        """
        self._facts.clear()

    def get(self, address: tuple):
        """Reads a value from the cube for a given address.
        If no records exist for the given idx_address, then 0.0 will be returned.
        :raises TinyOlapInvalidKeyError:
        """
        bolt = self._address_to_bolt(address)
        return self._get(bolt)

    def set(self, address: tuple, value):
        """Writes a value to the cube at the given address."""
        bolt = self._address_to_bolt(address)
        return self._set(bolt, value)

    def _get(self, bolt, bypass_rules=False, row_set=None):
        """
        Returns a value from the cube for a given idx_address.
        If no records exist for the given idx_address, then 0.0 will be returned.

        Info: The argument row_set is only used for the refresh of Views on cubes.
        """
        (super_level, idx_address) = bolt
        self._cell_request_counter += 1

        # ALL_LEVELS rules
        if not bypass_rules:
            # caching
            if self._caching and bolt in self._cache:
                self._cache_hit_counter += 1
                return self._cache[bolt]

            if self._has_rules:
                found, func = self._rules.match(scope=RuleScope.ALL_LEVELS, idx_address=idx_address)
                if found:
                    cursor = self._create_cell_from_bolt(None, (super_level, idx_address))
                    try:
                        self._rule_request_counter += 1
                        value = func(cursor)
                        if value != Cell.CONTINUE:
                            if self._caching:
                                self._cache[bolt] = value  # save value to cache
                            return value
                    except ZeroDivisionError:
                        return RuleError.DIV0
                    except KeyError as err:
                        return RuleError.REF
                    except Exception as err:
                        return RuleError.ERR

        if super_level == 0:  # base-level cells
            # BASE_LEVEL rules
            if not bypass_rules:
                if self._has_rules:
                    found, func = self._rules.match(scope=RuleScope.BASE_LEVEL, idx_address=idx_address)
                    if found:
                        cursor = self._create_cell_from_bolt(None, (super_level, idx_address))
                        try:
                            self._rule_request_counter += 1
                            value = func(cursor)
                            if value != Cell.CONTINUE:
                                if self._caching:
                                    self._cache[bolt] = value  # save value to cache
                                return value
                        except ZeroDivisionError:
                            return RuleError.DIV0
                        except Exception as err:
                            return RuleError.ERR

            # BASE_LEVEL values
            return self._facts.get(idx_address)

        else:  # aggregated cells
            # AGGREGATION_LEVEL
            if not bypass_rules:
                if self._has_rules:
                    found, func = self._rules.match(scope=RuleScope.AGGREGATION_LEVEL, idx_address=idx_address)
                    if found:
                        cursor = self._create_cell_from_bolt(None, (super_level, idx_address))
                        try:
                            self._rule_request_counter += 1
                            value = func(cursor)
                            if value != Cell.CONTINUE:
                                if self._caching:
                                    self._cache[bolt] = value  # save value to cache
                                return value
                        except ZeroDivisionError:
                            return RuleError.DIV0
                        except Exception as err:
                            return RuleError.ERR

            # *****************************************************************
            # THE FOLLOWING CODE IS HIGHLY PERFORMANCE OPTIMIZED!!!
            # This is the section where the roll up OLAP aggregations happen.
            # DO NOT CHANGE THE CODE WITHOUT PERFORMANCE IMPACT ANALYSIS!!!
            # *****************************************************************
            # get records row ids for current cell idx_address
            rows = self._facts.query(idx_address, row_set)
            self._aggregation_counter += len(rows)
            if not rows:
                return None  # no records, so nothing to aggregate

            # Check if we have a standard or a weighted aggregation.
            # Note: weighted aggregations are 2x up to 4x slower due to the weight lookup and multiplication
            weighted_aggregation, w_idx, w_lookup = self._weights.get_weighting(idx_address)
            total = 0.0
            facts = self._facts.facts # put object in local scope. this results in 16% faster code
            if weighted_aggregation:
                # weighted aggregation
                self._weighted_aggregation_counter += len(rows)
                addresses = self._facts.addresses  # put object in local scope. this results in 16% faster code
                # todo: add support for ROLL_UP rules
                value = 0.0  # LOL, this normally is an unnecessary assigment but makes the overall code 3% faster
                for row in rows:
                    value = facts[row]
                    if isinstance(value, float):  # makes the overall code 5% faster than 'if type(value) is float'
                        w = 1.0
                        for idx in w_idx:  # only process dimensions with non-standard (+1.0) weighting
                            # read the weight for the roll up of the current row member to its requested
                            # Note: when both are the same element, we normally would not have to execute the
                            # weight look up. But it turned out that an extra if statement is more expensive
                            # just do unnecessary multiplications.
                            w *= w_lookup[idx].get(addresses[row][idx], 1.0)
                        total += float(value) * w
            else:
                # default additive aggregation
                # todo: add support for ROLL_UP rules
                value = 0.0
                for row in rows:
                    value = facts[row]
                    if isinstance(value, float):  # makes the overall code 5% faster than 'if type(value) is float'
                        total += value
            if self._caching:
                self._cache[bolt] = total  # save value to cache
            return total

    def _set_base_level_cell(self, idx_address, value):
        """Writes a base level value to the cube for the given idx_address (idx_address and measures)."""
        self._facts.set(idx_address, value)
        if self._storage_provider and self._storage_provider.connected:
            if value:
                self._storage_provider.set_record(self._name, str(idx_address), json.dumps({"value": value}))
            else:
                self._storage_provider.set_record(self._name, str(idx_address))

    def _set(self, bolt, value, bypass_rules=False):
        """Writes a value to the cube for the given bolt (idx_address and measures)."""
        if self._caching and self._cache:
            self._cache = {}  # clear the cache

        (super_level, idx_address) = bolt

        if type(value) is int:
            value = float(value)

        if super_level == 0:  # for base-level cells...
            result = self._facts.set(idx_address, value)
            if self._storage_provider and self._storage_provider.connected:
                if value:
                    self._storage_provider.set_record(self._name, str(idx_address), json.dumps({"value": value}))
                else:
                    self._storage_provider.set_record(self._name, str(idx_address))

            #  ...check for base-level on_entry rule (aka push-rules) to be executed
            if not bypass_rules:
                if self._has_rules:
                    found, func = self._rules.match(scope=RuleScope.ON_ENTRY, idx_address=idx_address)
                    if found:
                        # cursor = self._create_cell_from_bolt(None, (super_level, idx_address, idx_measures))
                        cursor = self._create_cell_from_bolt(None, (super_level, idx_address))
                        try:
                            self._rule_request_counter += 1
                            func(cursor)
                        except Exception as err:
                            pass

        else:
            raise TinyOlapInvalidOperationError(f"Write back to aggregated cells in not (yet) supported.")

    def _update_aggregation_index(self, fact_table_index, address, row):
        """Updates all fact table index for all aggregations over all dimensions. FOR INTERNAL USE ONLY!"""
        for d, idx_member in enumerate(address):
            for idx_parent in self._dimensions[d].member_defs[address[d]][self._dimensions[d].ALL_PARENTS]:
                if idx_parent in fact_table_index._index[d]:
                    fact_table_index._index[d][idx_parent].add(row)
                else:
                    fact_table_index._index[d][idx_parent] = {row}

    # def _validate_address(self, address: tuple, measure):
    def _validate_address(self, address: tuple):
        if len(address) != self._dim_count:
            raise ValueError("Invalid number of dimensions in idx_address.")
        idx_address = list(range(0, self._dim_count))
        super_level = 0
        for d in range(0, self._dim_count):
            if address[d] in self._dimensions[d]._member_idx_lookup:
                idx_address[d] = self._dimensions[d]._member_idx_lookup[address[d]]
                super_level += self._dimensions[d].member_defs[idx_address[d]][self._dimensions[d].LEVEL]
            else:
                raise ValueError(f"'{address[d]}' is not a member of dimension '{self._dimensions[d]._name}'.")
        return tuple(idx_address), super_level

    def _remove_members(self, dimension, members):
        """Removes member from indexes and data table"""
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
            address.append(self._dimensions[i].member_defs[idx_address[i]][1])
        return address

    def _address_to_idx_address(self, address):
        """
        Converts an address to an idx_address index with member ids.
        :param address: The address to be converted.
        :return:
        """
        bolt = self._address_to_bolt(address)
        return bolt[1]

    def _address_to_bolt(self, address):
        """Converts a given address into a bolt.
        A bolt is a tuple of integer address, used for internal access of cells.
        """
        dim_count = self._dim_count
        dimensions = self._dimensions
        if len(address) != dim_count:
            raise TinyOlapInvalidAddressError(
                f"Invalid address. At least {self._dim_count} member_defs expected "
                f"for cube '{self._name}, but only {len(address)} where passed in.")

        # Validate member_defs

        idx_address = [None] * dim_count
        super_level = 0
        for i, member in enumerate(address[: dim_count]):
            dimension = dimensions[i]
            if member in dimension._member_idx_lookup:
                idx_address[i] = dimension._member_idx_lookup[member]
                super_level += dimension.member_defs[idx_address[i]][6]
            else:
                raise TinyOlapInvalidAddressError(f"Invalid idx_address. '{member}' is not a member of the {i}. "
                                                         f"dimension '{dimension.name}' in cube {self._name}.")
        idx_address = tuple(idx_address)

        return super_level, idx_address  # that's the 'bolt'

    # endregion

    # region cells
    def cell(self, *args) -> Cell:
        """Returns a new Cell from the Cube."""
        return Cell.create(self, self._dim_lookup, args, self._address_to_bolt(args))

    def _create_cell_from_bolt(self, address, bolt) -> Cell:
        """Create a Cell for the Cube directly from an existing bolt."""
        return Cell.create(self, self._dim_lookup, address, bolt)

    def _get_default_cell_address(self):
        """Generates a default address. This is the first member from all dimensions."""
        address = []
        for dim in self._dimensions:
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

        :return: A json string representing the cube.
        """
        names = [dim.name for dim in self._dimensions]
        config = {"content": "cube",
                  "name": self.name,
                  "description": self._description,
                  "dimensions": names,
                  "caching": self._caching,
                  "rules": len(self._rules),
                  }

        json_string = json.dumps(config, indent=4)
        return json_string

    # todo: adjust to fully support cube objects (e.g. rules, subsets)
    def from_json(self, json_string: str):
        """
        Initializes the cube from a json string.

        .. warning::
            Calling this method for cubes which are already in use (contain data)
            will very likely **corrupt your database!** Calling this method is only save
            **before** you write any data to a cube. Handle with care.

        :param json_string: The json string containing the cube definition.
        :raises TinyOlapFatalError: Raised if an error occurred during the deserialization from json string.
        """
        try:
            # read configuration
            config = json.loads(json_string)
            self._name = config["name"]
            self._description = config["description"]
            new_names = config["dimensions"]
            self._dimensions = tuple([self._database.dimensions[name] for name in new_names])
            self._caching = config["caching"]

            self._dim_count = len(self._dimensions)
            self._names = []
            self._dim_lookup = CaseInsensitiveDict([(dim.name, idx) for idx, dim in enumerate(self._dimensions)])
            self._facts = FactTable(self._dim_count, self)

            # load data
            if self._storage_provider:
                records = self._storage_provider.get_records(self._name)
                for record in records:
                    address = str(record[0])
                    idx_address = tuple(map(int, address[1:-1].split(sep=",")))

                    data = json.loads(record[1])
                    for key, value in data.items():
                        self._set_base_level_cell(idx_address, value)

            # initialize rules
            # Note: This should to be done after loading the data, as otherwise push rules
            #       might be triggered and recalculated although the data is (should be) already consistent.
            if config["rules"] > 0:
                pass
            functions = self._database._code_manager.get_functions(self._name)
            for f in functions:
                self.register_rule(function=f.function, trigger=f.trigger,
                                   scope=f.scope, injection=f.injection, code=f._code)

        except Exception as err:
            raise TinyOlapFatalError(f"Failed to load json for dimension '{self.name}'. {str(err)}")
    # endregion

    # region Rules
    # def remove_rule(self, pattern: list[str]) -> bool:
    #     """
    #     Removes (unregisters) a rule function from the cube.
    #
    #     :param pattern: The trigger of the rule to be removed.
    #     :return: ``True``, if a function with the given trigger was found and removed, ``False`` otherwise.
    #     """
    #     return NotImplemented
    #
    # def remove_all_rules(self):
    #     """
    #     Removes all rule functions from the cube.
    #     """
    #     return NotImplemented

    def register_rule(self, function, trigger: list[str] = None,
                      scope: RuleScope = RuleScope.ALL_LEVELS,
                      injection: RuleInjectionStrategy = RuleInjectionStrategy.NO_INJECTION,
                      code: str = None):
        """
        Registers a rule function for the cube. Rules function either need to be decorated with the ``@rules(...)``
        decorator or the arguments ``trigger`` and ``scope`` of the ``add_rules(...)`` function must be specified.

        :param code: (optional)Source code of the function.
        :param injection: The injection strategy defined for the function.
        :param function: The rules function to be called.
        :param trigger: The cell idx_address trigger that should trigger the rule.
        :param scope: The scope of the rule.
        """

        offset = 0
        if not inspect.isroutine(function):
            if callable(function) and function.__name__ == "<lambda>":
                offset = 1
            else:
                raise TinyOlapRuleError(
                    f"Argument 'function' does not seem to be a Python function, type id '{type(function)}'.")

        # validate function and decorator parameters
        function_name = str(function).split(" ")[1 + offset]
        cube_name = self.name
        if hasattr(function, "cube"):
            cube_name = function.cube
            if cube_name.lower() != self.name.lower():
                raise TinyOlapRuleError(
                    f"Failed to add rule function. Function '{function_name}' does not seem to be associated "
                    f"with this cube '{self.name}', but with cube '{cube_name}'.")
        if not trigger:
            if hasattr(function, "trigger"):
                trigger = function.trigger
                if type(trigger) is str:
                    trigger = [trigger, ]
                if not type(trigger) is list:
                    raise TinyOlapRuleError(f"Failed to add rule function. Argument 'trigger' is not of the expected "
                                        f"type 'list(str)' but of type '{type(trigger)}'.")
            else:
                raise TinyOlapRuleError(f"Failed to add rule function. Argument 'trigger' missing for "
                                    f"function {function_name}'. Use the '@rule(...) decorator from tinyolap.decorators.")

        if not scope:
            if hasattr(function, "scope"):
                scope = function.scope
                if not (str(type(scope)) == str(type(RuleScope.ROLL_UP))):
                    raise TinyOlapRuleError(f"Failed to add rule function. Argument 'scope' is not of the expected "
                                        f"type ''{type(RuleScope.ALL_LEVELS)}' but of type '{type(scope)}'.")
            else:
                raise TinyOlapRuleError(f"Failed to add rule function. Argument 'scope' missing for "
                                    f"function {function_name}'. Use the '@rule(...) decorator from tinyolap.decorators.")
        if not injection:
            if hasattr(function, "injection"):
                injection = function.injection
            else:
                injection = RuleInjectionStrategy.NO_INJECTION

        if type(trigger) is str:  # a lazy user forgot to put the trigger in brackets
            trigger = [trigger, ]

        # setup and add rule
        try:
            idx_pattern = self._pattern_to_idx_pattern(trigger)
            rule = Rule(function=function, name=function_name, cube=self.name, trigger=trigger,
                        idx_trigger_pattern=idx_pattern,
                        scope=scope, injection=injection, code=code)
            self._rules.add(rule)
        except Exception as err:
            raise TinyOlapRuleError(f"Failed to add rule function '{function_name}' "
                                    f"to cube '{self.name}', invalid target definition found. {err}")

        # add function to code manager
        self._database._code_manager.register_function(
            function=function, cube=cube_name, trigger=trigger,
            scope=scope, injection=injection, code=code)

        self._has_rules = (len(self._rules) > 0)

    def validate_rules(self, save_after_successful_validation: bool = True) -> (bool, str):
        """
        Validates all registered rules by calling each with a random cell matching the defined
        rule trigger and rule scope. Calling this method (maybe even multiple times) can be
        useful for high-level rules testing.

        .. warning::
            Calling this method does not replace proper rule testing. Especially when your
            database should be used by other users or for professional purposes you need to ensure
            that your rule calculations ideally never (or only for explicit purposes) will throw
            errors.

        :param save_after_successful_validation: If set to true
        :return: ``(True, validation_results_json:str)`` if all rules returned a proper result without causing errors.
                 ``(False, validation_results_json:str)`` if at least one rule causes an error. The validation results
                  will contain information for all rules that have been processed. The validation will not stop
                  on the first error casued by a rule function.
        """
        # todo: to be implemented

        # update the database
        if save_after_successful_validation:
            self._database.save()
        return True

    def _pattern_to_idx_pattern(self, pattern):
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

