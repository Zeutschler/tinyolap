# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import copy
from collections import Iterable

from tinyolap.member import Member


class Area:
    """
    An Area represents a subspace of a cube. Areas are intended be used for mass operations on cube cells.
    The following example should explain the basic concept:

    .. code:: python

        area = cube.area("Jan", "2023", "Plan")
        # clears all data for months='Jan', years='2023' and datatype='Plan' over all other dimensions.
        area.clear()

        # Copies all data from 'Actual', '2022', increases all values by 15% and writes them to the 'Plan' for '2023'.
        # Info: All data in the target area will be deleted before hand.
        # Info: Depending on the amount of data to be copied, such operations may take some time (a few seconds).
        cube.area("Plan", "2023") = cube.area("Actual", "2022") * 1,15

    The smallest possible subspace would be a single cube cell.
    For such purposes it is recommended to use the Cell object.
    """

    def __init__(self, cube, args):
        """
        Initializes a new data area for a specific cube.
        :param cube: The cube to create the data area for.
        :param args: The member specification for the data area.
        """
        self._cube = cube
        self._args = args
        self._area_def = []
        self._idx_area_def = []
        self._levels_area_def = []
        self._validate(args)
        self._rows = set()
        self._modifiers = []
        self._func = None

    def __len__(self):
        if not self._rows:
            # refresh dat area
            rows = self._cube._facts.query_area(self._idx_area_def)
            self._rows = rows

        return len(self._rows)

    # region Area manipulation via indexing/slicing
    def __getitem__(self, args):
        return self.clone().alter(args)

    def __setitem__(self, args, value):
        if type(value) is Area:
            item_area = self.clone().alter(args)
            item_area._apply_other_area(args, value)
        else:
            item_area = self.clone().alter(args)
            item_area.set_value(value)

    def __delitem__(self, args):
        item_area = self.clone().alter(args)
        item_area.clear()

    # endregion

    def records(self, include_cube_name: bool = False, as_list: bool = True):
        """
        Generator to loop over existing items of the data area.
        Returns nested tuples in the form ((dim_member1, ... , dim_memberN), value).
        """
        # if not self._rows:
        # refresh dat area
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows

        facts = self._cube._facts
        for row in self._rows:
            idx_address = facts.addresses[row]
            record = self._cube._idx_address_to_address(idx_address, include_cube_name=include_cube_name)

            if as_list:
                for key in facts.facts[row]:
                    value = facts.facts[row][key]
                    record.append(value)
            else:
                values = tuple(facts.facts[row].values())
                record = [tuple(record), values]

            yield record

    def addresses(self, include_cube_name: bool = False):
        """
        Generator to loop over existing addresses of the data area.
        Returns tuples in the form (dim_member1, ... , dim_memberN).
        """
        if not self._rows:
            # refresh dat area
            rows = self._cube._facts.query_area(self._idx_area_def)
            self._rows = rows

        facts = self._cube._facts
        for row in self._rows:
            idx_address = facts.addresses[row]
            yield self._cube._idx_address_to_address(idx_address, include_cube_name=include_cube_name)

    def alter(self, *args) -> Area:
        """Alters the data area, based on the given arguments."""
        self._validate(args, alter=True)
        self.refresh()
        return self

    def clone(self) -> Area:
        """Creates a copy of the data area."""
        cloned = copy.copy(self)
        return cloned

    def refresh(self):
        self._rows = self._cube._facts.query_area(self._idx_area_def)

    def clear(self):
        """
        Clears the data area. All cells holding values will be removed from the cube.
        """
        if not self._rows:
            rows = self._cube._facts.query_area(self._idx_area_def)
        else:
            rows = self._rows
        self._cube._facts.remove_records(rows)
        self._rows = set()

    def set_value(self, value):
        """
        Sets all existing cells of the data area to a specific value.
        :param value: The value to be set.
        """
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for k in facts[row]:
                facts[row][k] = value

    def multiply(self, factor: float):
        """
        Multiplies all existing cells holding numeric values with a certain factor.
        :type factor: The factor to multiply all cells holding numeric values with.
        """
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for k, v in facts[row].items():
                if type(v) is float:
                    facts[row][k] = v * factor

    def increment(self, value: float):
        """
        Increments all existing cells holding numeric values by a certain value.
        :type value: The value to increment all cells holding numeric values by.
        """
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for k, v in facts[row].items():
                if type(v) is float:
                    facts[row][k] = v + value

    def min(self):
        """
        Returns the minimum value of all existing numeric cells in the data area.
        """
        minimum = None
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for v in facts[row].values():
                if type(v) is float:
                    if not minimum:
                        minimum = v
                    if v < minimum:
                        minimum = v
        return minimum

    def max(self):
        """
        Returns the maximum value of all existing numeric cells in the data area.
        """
        maximum = None
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for v in facts[row].values():
                if type(v) is float:
                    if not maximum:
                        maximum = v
                    if v > maximum:
                        maximum = v
        return maximum

    def avg(self):
        """
        Returns the average of all existing numeric cells in the data area.
        """
        avg = 0.0
        z = 0
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for v in facts[row].values():
                if type(v) is float:
                    avg += v
                    z += 1
        if z == 0:
            return None
        return avg / z

    def sum(self):
        """
        Returns the sum of all existing numeric cells in the data area.
        """
        total = 0.0
        z = 0
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        for row in rows:
            for v in facts[row].values():
                if type(v) is float:
                    total += v
                    z += 1
        if z == 0:
            return None
        return total

    def to_json(self, compact: bool = True):
        """
        Returns a data area as a json string, including the definition of the area
        and all base level cell data from that area. For larger data areas it is
        recommended to set parameter ``compact`` to ``True`` (the default value).
        This reduces the size of the returned json string by factor 2 to 10.

        The json returned by this method will identical to calling ``json.dumps(area.to_dict())`` .

        This function is intended to be used for custom persistence.
        If you just want to temporarily keep data (e.g. to undo certain changes),
        in memory, then consider to use method ``to_dict()`` for better performance
        instead.

        :param compact: Identifies is the data area should be compacted.
        """
        return NotImplemented

    def from_json(self, json: str, validate: bool = False) -> bool:
        """
        Reads a data area from a json string, clears the data area and
        writes (imports) all values contained in the data area definition into the cube.

        :param json: A json string containing the data area definition.
        :param validate: If set to ``True`` , the data area will be validated before importing.
        By this you can ensure that all values of the data area can be written to the cube.
        If at least one value of the data area can not be written to the cube, then ```from_json()``
        will stop and return ``False`` , otherwise the method will continue and start to write
        (import) values to the cube.
        :return Returns ``True``if the import was successful, ``False``otherwise.
        """
        return NotImplemented

    def to_dict(self, compact: bool = True):
        """
        Returns a data area as a Python ``dict`` object. For larger data areas it is
        recommended to set parameter ``compact`` to ``True`` (the default value).
        This reduces the memory footprint of the returned dict by factor 2 to 10.

        :param compact: Identifies is the data area should be compacted.
        """
        return NotImplemented

    def from_dict(self, area_dict: dict, validate: bool = False) -> bool:
        """
        Reads a data area from a Python dict object, clears the data area and
        writes (imports) all values contained in the data area definition into the cube.

        :param area_dict: A Python dict object containing the data area definition.
        :param validate: If set to ``True`` , the data area will be validated before importing.
        By this you can ensure that all values of the data area can be written to the cube.
        If at least one value of the data area can not be written to the cube, then ```from_dict()``
        will stop and return ``False`` , otherwise the method will continue and start to write
        (import) values to the cube.
        :return Returns ``True``if the import was successful, ``False``otherwise.
        """
        return NotImplemented

    # region operator overloading for numerical operations
    def __add__(self, other):  # + operator
        self._func = lambda x: x + other
        return self

    def __iadd__(self, other):  # += operator
        self._func = lambda x: x + other
        return self

    def __radd__(self, other):  # + operator
        self._func = lambda x: x + other
        return self

    def __sub__(self, other):  # - operator
        self._func = lambda x: x - other
        return self

    def __isub__(self, other):  # -= operator
        self._func = lambda x: x - other
        return self

    def __rsub__(self, other):  # - operator
        self._func = lambda x: x - other
        return self

    def __mul__(self, other):  # * operator
        self._func = lambda x: x * other
        return self

    def __imul__(self, other):  # *= operator
        self._func = lambda x: x * other
        return self

    def __rmul__(self, other):  # * operator
        self._func = lambda x: x * other
        return self

    def __truediv__(self, other):  # / operator (returns an float)
        self._func = lambda x: x / other
        return self

    def __idiv__(self, other):  # /= operator (returns an float)
        self._func = lambda x: x / other
        return self

    def __rtruediv__(self, other):  # / operator (returns an float)
        self._func = lambda x: x / other
        return self

    def __floordiv__(self, other):  # // operator (returns an integer)
        self._func = lambda x: x // other
        return self

    def __ifloordiv__(self, other):  # //= operator (returns an integer)
        self._func = lambda x: x // other
        return self

    def __rfloordiv__(self, other):  # // operator (returns an integer)
        self._func = lambda x: x // other
        return self

    # endregion

    def _validate(self, args, alter: bool = False):

        # reset area definition
        dim_count = self._cube.dimensions_count

        if alter:
            self._modifiers = []
        else:
            self._area_def = [None] * dim_count
            self._idx_area_def = [None] * dim_count
            self._levels_area_def = [None] * dim_count

        already_used = set()
        for arg in args:
            idx_dim, members, idx_members, level_members = self.__get_members(arg)

            if not alter:
                if idx_dim in already_used:
                    raise TypeError(f"Duplicate member definition argument '{str(arg)}'. The dimension of these members"
                                    f"have already been defined in the area definition.")
                already_used.add(idx_dim)
            else:
                self._modifiers.append([idx_dim, members, idx_members, level_members])

            self._area_def[idx_dim] = members
            self._idx_area_def[idx_dim] = idx_members
            self._levels_area_def[idx_dim] = level_members

    def __get_members(self, item):
        idx_dims = []
        members = []
        idx_members = []
        level_members = []
        dim_names = [key for key in self._cube._dim_lookup.keys()]

        if type(item) is str or not isinstance(item, Iterable):
            item = (item,)

        for member in item:
            if type(member) is Member:
                idx_dims.append(member._idx_dim)
                members.append(member.name)
                idx_members.append(member._idx_member)
                level_members.append(member._member_level)

            elif type(member) is str:
                idx_dim, idx_member, member_level = self._get_member(dim_names, member)
                idx_dims.append(idx_dim)
                members.append(member)
                idx_members.append(idx_member)
                level_members.append(member_level)
            else:
                raise TypeError(f"Invalid type '{type(item)}'. Only type 'str', 'list' or 'tuple' "
                                f"supported for members in Area definition.")

        # ensure all members are from the same dimension
        idx_dim = idx_dims[0]
        for idx in idx_dims[1:]:
            if idx != idx_dim:
                raise TypeError(f"Invalid member definition argument '{str(item)}'. Members do not belong "
                                f"to one dimension only, multiple dimensions found.")

        return idx_dim, members, idx_members, level_members

    def _get_member(self, dim_names, member_name: str):
        level = self._cube._dimensions[0].LEVEL
        dimensions = self._cube._dimensions
        idx_dim = -1
        idx_member = -1
        pos = member_name.find(":")
        if pos != -1:
            # lets extract the dimension name and check if it is valid, e.g., c["months:Mar"]
            dim_name = member_name[:pos].strip()

            # special test for ordinal dim position instead of dim name, e.g., c["1:Mar"] = 333.0
            if dim_name.isdigit():
                ordinal = int(dim_name)
                if 0 <= ordinal < len(dim_names):
                    # that's a valid dimension position number
                    idx_dim = ordinal
            if idx_dim == -1:
                if dim_name not in self._cube._dim_lookup:
                    raise KeyError(f"Invalid member key. '{dim_name}' is not a dimension "
                                   f"in cube '{self._cube.name}. Found in '{member_name}'.")
                idx_dim = self._cube._dim_lookup[dim_name]

            # adjust the member name
            member_name = member_name[pos + 1:].strip()
            if member_name not in dimensions[idx_dim]._member_idx_lookup:
                raise KeyError(f"Invalid member key. '{member_name}'is not a member of "
                               f"dimension '{dim_name}' in cube '{self._cube.name}.")
            idx_member = dimensions[idx_dim]._member_idx_lookup[member_name]

            member_level = dimensions[idx_dim].members[idx_member][self._cube._dimensions[0].LEVEL]
            return idx_dim, idx_member, member_level

        # No dimension identifier in member name, search all dimensions
        for idx_dim in range(self._cube.dimensions_count):
            if member_name in dimensions[idx_dim]._member_idx_lookup:
                idx_member = dimensions[idx_dim]._member_idx_lookup[member_name]
                # adjust the super_level
                member_level = dimensions[idx_dim].members[idx_member][level]
                return idx_dim, idx_member, member_level

        # You loose...
        if idx_dim == -1:
            raise KeyError(f"'{member_name}' is not a member of any dimension in "
                           f"cube '{self._cube.name}', or a valid reference to any of it's dimensions.")

    def _apply_other_area(self, args, other: Area):
        if not (self._cube.name is other._cube.name):
            raise KeyError(f"Unsupported area operations. Areas need to be from one cube, "
                           f"but one area is from cube '{self._cube.name}' "
                           f"and the other from cube '{other._cube.name}' .")

        if self._modifiers:

            if not self.modifiers_of_same_scope(self._modifiers, other._modifiers):
                raise KeyError(f"Unsupported area operations. Areas modifiers need to"
                               f"address the same dimensions and the same number of members, "
                               f"e.g.: a['Jan'] = a['Feb'] would be valid, but "
                               f"a['Jan'] = a['2022'] would not be valid, because of different dimensions.")

            if not self.identical_modifiers(self._modifiers, other._modifiers):
                self.clear()

            if not other._rows:
                other.refresh()

            facts = other._cube._facts
            for row in other._rows:
                idx_address = list(facts.addresses[row])
                for modifier in self._modifiers:
                    idx_dim = modifier[0]
                    idx_member = modifier[2][0]
                    idx_address[idx_dim] = idx_member

                for key in facts.facts[row]:
                    value = facts.facts[row][key]
                    if other._func:
                        value = other._func(value)
                    bolt = (0, tuple(idx_address), key)
                    self._cube._set(bolt, value)
                    # print(f"{idx_address} >>> {self._cube._idx_address_to_address(idx_address)}:= {value} is {self._cube._get(bolt)}")

    def identical_modifiers(self, modifiers_a, modifiers_b) -> bool:
        if len(modifiers_a) != len(modifiers_b):
            return False
        for a, b in zip(modifiers_a, modifiers_b):
            idx_dim_a, members_a, idx_members_a, level_members_a = a
            idx_dim_b, members_b, idx_members_b, level_members_b = b
            if idx_dim_a != idx_dim_b:
                return False
            if tuple(idx_members_a) != tuple(idx_members_b):
                return False
        return True

    def modifiers_of_same_scope(self, modifiers_a, modifiers_b) -> bool:
        if len(modifiers_a) != len(modifiers_b):
            return False
        for a, b in zip(modifiers_a, modifiers_b):
            idx_dim_a, members_a, idx_members_a, level_members_a = a
            idx_dim_b, members_b, idx_members_b, level_members_b = b
            if idx_dim_a != idx_dim_b:
                return False
            if len(idx_members_a) != len(idx_members_b):
                return False
        return True

    def merge_modifier_into(self, modifiers_a, modifiers_b) -> bool:
        # todo: implement this...
        raise NotImplementedError()

