# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import copy
import itertools
from collections import Iterable

from tinyolap.exceptions import TinyOlapInvalidAddressError
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
        # Info: All data in the target area will be deleted beforehand.
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
        self._pinned = False
        self._pinned_records = []

    def __len__(self):
        if not self._rows:
            # refresh dat area
            rows = self._cube._facts.query_area(self._idx_area_def)
            self._rows = rows

        return len(self._rows)

    # region Area manipulation via indexing/slicing
    def __getitem__(self, args):
        area = self.clone().alter(args)
        # We need to pin (freeze) the current state and data of the area
        # as source and target area in area-operations can overlap (or even be identical)
        # and would cause inconsistent operations. Lazy operations (using 'yield') would fail.
        area._pinned = True
        area._pinned_records = area._raw_records()
        return area

    def __setitem__(self, args, value):
        if type(value) is Area:
            area = self.clone().alter(args)
            area._apply_other_area(args, value)
        else:
            area = self.clone().alter(args)
            area.set_value(value)

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

            # if as_list:
            #     for key in facts.facts[row]:
            #         value = facts.facts[row][key]
            #         record.append(value)
            # else:
            #     values = tuple(facts.facts[row].values())
            #     record = [tuple(record), values]

            if as_list:
                record.append(facts.facts[row])
            else:
                record = [tuple(record), facts.facts[row]]

            yield record

    def _raw_records(self) -> list:
        """
        Generator to loop over existing items of the data area.
        Returns nested tuples in the form ((dim_member1, ... , dim_memberN), value).
        """
        # if not self._rows:
        # refresh data area
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        records = []
        facts = self._cube._facts

        for row in self._rows:
            # idx_address = facts.addresses[row]
            record = list(facts.addresses[row])
            # for key in facts.facts[row]:
            #     value = facts.facts[row][key]
            #     record.append(value)

            # create a (idx_address, value) tuple for direct use
            # records.append((record, dict(facts.facts[row])))
            records.append((record, facts.facts[row],))
        return records

    def addresses(self, include_cube_name: bool = False, enumerate_data_space: bool = False,
                  include_value: bool = False):
        """
        Generator to loop over existing addresses of the data area.
        Returns tuples in the form (dim_member1, ... , dim_memberN).
        :param include_cube_name: Identifies if the name of the cube should be
        included in the address tuple.
        :param enumerate_data_space: Identifies if the entire data space, independent of
        value exists or not should be returned. Caution, the data space can be hugh.
        :param include_value: Identifies if the actual values of the records should be returned.
        """
        if enumerate_data_space:
            member_lists = []
            for dim_idx, axis in enumerate(self._idx_area_def):
                dimension = self._cube._dimensions[dim_idx]
                if axis:
                    member_list = []
                    if type(axis) is int:
                        member = dimension.member_defs[axis][1]
                        member_list.extend(dimension.member_get_leaves(member))
                    else:
                        for item in axis:
                            member = dimension.member_defs[item][1]
                            member_list.extend(dimension.member_get_leaves(member))
                    member_lists.append(member_list)
                else:
                    # get all base member_defs from dimension
                    member_lists.append(dimension.get_leaves())

            if include_cube_name:
                cube = (self._cube.name,)
                for address in itertools.product(*member_lists):
                    if include_value:
                        yield cube + address + (self._cube[address],)
                    else:
                        yield cube + address
            else:
                for address in itertools.product(*member_lists):
                    if include_value:
                        yield address + (self._cube[address],)
                    else:
                        yield address

        else:
            if not self._rows:
                # refresh dat area
                rows = self._cube._facts.query_area(self._idx_area_def)
                self._rows = rows

            facts = self._cube._facts
            for row in self._rows:
                idx_address = facts.addresses[row]
                yield self._cube._idx_address_to_address(idx_address, include_cube_name=include_cube_name)

    def enumerate(self, include_cube_name: bool = False):
        """
        Generator to loop over all addresses of the data area. It enumerates the entire space.
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
        # self._modifiers = []
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

    def _compatible(self, other: Area) -> (bool, str):
        """Evaluates if two areas are compatible.
           Checks whether the dimensions are identical,
           1 member per defined dimension only
           and if all member_defs are base level member_defs.
            :param other: The other area to be checked.
        """
        if self._cube != other._cube:
            return False, f"Incompatible areas from different cubes."

        for d in range(self._cube.dimensions_count):
            if self._area_def[d] and other._area_def[d]:
                dimension = self._cube._dimensions[d]
                # check for 1 member per dimension
                if len(self._area_def[d]) > 1:
                    return False, f"Incompatible areas. The left area of the operation defines " \
                                  f"{len(self._area_def[d])} member_defs for dimension '{dimension.name}', " \
                                  f"but only 1 member per dimension is allowed."
                if len(other._area_def[d]) > 1:
                    return False, f"Incompatible areas. The right area of the operation defines " \
                                  f"{len(other._area_def[d])} member_defs for dimension '{dimension.name}', " \
                                  f"but only 1 member per dimension is allowed."

                # check for member_defs are base level member_defs
                if not dimension.member_is_leave(self._area_def[d][0]):
                    return False, f"Incompatible areas. The left side of operations defines the member " \
                                  f"'{self._area_def[d]}' for dimension '{dimension.name}' which is not a " \
                                  f"leave-level member. Only leave-level member_defs are supported."
                if not dimension.member_is_leave(other._area_def[d][0]):
                    return False, f"Incompatible areas. The right side of operations defines the member " \
                                  f"'{other._area_def[d]}' for dimension '{dimension.name}' which is not a " \
                                  f"leave-level member. Only leave-level member_defs are supported."

            elif (not self._area_def[d]) and (not other._area_def[d]):
                pass  # dimension not defined for both areas, that's ok!
            else:
                if not self._area_def[d]:
                    return False, f"Incompatible areas. Left side of operations does not define a member " \
                                  f"for dimension '{self._cube._dimensions[d].name}', but the right side does."
                else:
                    return False, f"Incompatible areas. Right side of operations does not define a member " \
                                  f"for dimension '{self._cube._dimensions[d].name}', but the left side does."

        return True, None

    def set_value(self, value, enumerate_data_space: bool = False):
        """
        Sets all existing cells of the data area to a specific value.
        :param enumerate_data_space: Will force the enumerate the entire data space.
        :param value: The value to be set.
        """

        if type(value) is Area:
            # copy data from one area to another
            scr: Area = value
            dest: Area = self
            # ensure if dimensions are identical and 1 member per dimension and all member_defs are base level member_defs
            compatible, message = self._compatible(dest)
            if not compatible:
                raise TinyOlapInvalidAddressError(f"Set value failed. {message}")

            # clear the destination first
            dest.clear()

            # copy data from source to destination
            idx = [d for d, v in enumerate(self._area_def) if v]  # evalue which indexes need to be processed
            for address in scr.addresses(False, True, True):
                # adjust source address to target area
                new_address = list(address[:-1])
                for i in idx:
                    new_address[i] = self._area_def[i][0]  # adjust source address to target area

                new_value = address[-1]
                if scr._func:
                    new_value = scr._func(new_value)
                self._cube.set(new_address, new_value)



        else:

            if enumerate_data_space:
                rows = None
            else:
                rows = self._cube._facts.query_area(self._idx_area_def)
            if not rows:
                # empty data area
                # write to the entire data space
                if callable(value):
                    for address in self.addresses(False, True):
                        self._cube.set(address, value())
                else:
                    for address in self.addresses(False, True):
                        self._cube.set(address, value)

            else:
                self._rows = rows
                facts = self._cube._facts.facts
                # if callable(value):
                #     for row in rows:
                #         for k in facts[row]:
                #             facts[row][k] = value()
                # else:
                #     for row in rows:
                #         for k in facts[row]:
                #             facts[row][k] = value

                if callable(value):
                    for row in rows:
                        facts[row] = value()
                else:
                    for row in rows:
                        facts[row] = value




    def multiply(self, factor: float):
        """
        Multiplies all existing cells holding numeric values with a certain factor.
        :type factor: The factor to multiply all cells holding numeric values with.
        """
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        # for row in rows:
        #     for k, v in facts[row].items():
        #         if type(v) is float:
        #             facts[row][k] = v * factor
        for row in rows:
            v = facts[row]
            if type(v) is float:
                facts[row] = v * factor

    def increment(self, value: float):
        """
        Increments all existing cells holding numeric values by a certain value.
        :type value: The value to increment all cells holding numeric values by.
        """
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        # for row in rows:
        #     for k, v in facts[row].items():
        #         if type(v) is float:
        #             facts[row][k] = v + value
        for row in rows:
            v = facts[row]
            if type(v) is float:
                facts[row] = v + value

    def min(self):
        """
        Returns the minimum value of all existing numeric cells in the data area.
        """
        minimum = None
        rows = self._cube._facts.query_area(self._idx_area_def)
        self._rows = rows
        facts = self._cube._facts.facts
        # for row in rows:
        #     for v in facts[row].values():
        #         if type(v) is float:
        #             if not minimum:
        #                 minimum = v
        #             if v < minimum:
        #                 minimum = v
        for row in rows:
            v = facts[row]
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
        # for row in rows:
        #     for v in facts[row].values():
        #         if type(v) is float:
        #             if not maximum:
        #                 maximum = v
        #             if v > maximum:
        #                 maximum = v
        for row in rows:
            v = facts[row]
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
        # for row in rows:
        #     for v in facts[row].values():
        #         if type(v) is float:
        #             avg += v
        #             z += 1
        for row in rows:
            v = facts[row]
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
        # for row in rows:
        #     for v in facts[row].values():
        #         if type(v) is float:
        #             total += v
        #             z += 1
        for row in rows:
            v = facts[row]
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
        raise NotImplementedError()

    def from_json(self, json: str, validate: bool = False) -> bool:
        """
        Reads a data area from a json string, clears the data area and
        writes (imports) all values contained in the data area definition into the cube.

        :param json: A json string containing the data area definition.

        :param validate: If set to ``True`` , the data area will be validated before importing.
            By this you can ensure that all values of the data area can be written to the cube.
            If at least one value of the data area can not be written to the cube, then ``from_json()`` will
            stop and return ``False`` , otherwise the method will continue and start to write
            (import) values to the cube.

        :return: Returns ``True`` if the import was successful, ``False`` otherwise.
        """
        raise NotImplementedError()

    def to_dict(self, compact: bool = True):
        """
        Returns a data area as a Python ``dict`` object. For larger data areas it is
        recommended to set parameter ``compact`` to ``True`` (the default value).
        This reduces the memory footprint of the returned dict by factor 2 to 10.

        :param compact: Identifies is the data area should be compacted.
        """
        raise NotImplementedError()

    def from_dict(self, area_dict: dict, validate: bool = False) -> bool:
        """
        Reads a data area from a Python dict object, clears the data area and
        writes (imports) all values contained in the data area definition into the cube.

        :param area_dict: A Python dict object containing the data area definition.

        :param validate: If set to ``True`` , the data area will be validated before importing.
            By this you can ensure that all values of the data area can be written to the cube.
            If at least one value of the data area can not be written to the cube, then ``from_dict()`` will
            stop and return ``False`` , otherwise the method will continue and start to write
            (import) values to the cube.

        :return: Returns ``True`` if the import was successful, ``False`` otherwise.
        """
        raise NotImplementedError()

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
        if type(args) is tuple and len(args):
            if type(args[0]) is tuple:
                args = args[0]

        for arg in args:
            try:
                idx_dim, members, idx_members, level_members = self._get_members(arg)
            except:
                raise TinyOlapInvalidAddressError(f"Invalid member definition. Argument '{str(arg)}' is not "
                                                        f"a member of any dimension in cube '{self._cube.name}'")

            if not alter:
                if idx_dim in already_used:
                    raise TypeError(f"Duplicate member definition argument '{str(arg)}'. The dimension of these member_defs"
                                    f"have already been defined in the area definition.")
                already_used.add(idx_dim)
            else:
                self._modifiers.append([idx_dim, members, idx_members, level_members])

            self._area_def[idx_dim] = members
            self._idx_area_def[idx_dim] = idx_members
            self._levels_area_def[idx_dim] = level_members

    def _get_members(self, item):
        idx_dims = []
        members = []
        idx_members = []
        level_members = []
        names = [key for key in self._cube._dim_lookup.keys()]

        if type(item) is str or not isinstance(item, Iterable):
            item = (item,)

        for member in item:
            if type(member) is Member:
                idx_dims.append(member._idx_dim)
                members.append(member.name)
                idx_members.append(member._idx_member)
                level_members.append(member._member_level)

            elif type(member) is str:
                idx_dim, idx_member, member_level = self._get_member(names, member)
                idx_dims.append(idx_dim)
                members.append(member)
                idx_members.append(idx_member)
                level_members.append(member_level)
            else:
                raise TypeError(f"Invalid type '{type(item)}'. Only type 'str', 'list' or 'tuple' "
                                f"supported for member_defs in Area definition.")

        # ensure all member_defs are from the same dimension
        # todo: NO!!! Wrong behaviour! Areas shifts should support multiple dimensions.
        #       We need this to be possible: ... area(('Jan', 'Feb), '2021', 'name of subset')
        idx_dim = idx_dims[0]
        for idx in idx_dims[1:]:
            if idx != idx_dim:
                # raise TinyOlapInvalidAddressError(f"Invalid member definition argument '{str(item)}'. Members do not belong "
                #                f"to one dimension only, multiple dimensions found.")
                a = 1

        return idx_dim, members, idx_members, level_members

    def _get_member(self, names, member_name: str):
        level = self._cube._dimensions[0].LEVEL
        dimensions = self._cube._dimensions
        idx_dim = -1
        idx_member = -1
        pos = member_name.find(":")
        if pos != -1:
            # let's extract the dimension name and check if it is valid, e.g., c["months:Mar"]
            name = member_name[:pos].strip()

            # special test for ordinal dim position instead of dim name, e.g., c["1:Mar"] = 333.0
            if name.isdigit():
                ordinal = int(name)
                if 0 <= ordinal < len(names):
                    # that's a valid dimension position number
                    idx_dim = ordinal
            if idx_dim == -1:
                if name not in self._cube._dim_lookup:
                    raise KeyError(f"Invalid member key. '{name}' is not a dimension "
                                   f"in cube '{self._cube.name}. Found in '{member_name}'.")
                idx_dim = self._cube._dim_lookup[name]

            # adjust the member name
            member_name = member_name[pos + 1:].strip()
            if member_name not in dimensions[idx_dim]._member_idx_lookup:
                raise KeyError(f"Invalid member key. '{member_name}'is not a member of "
                               f"dimension '{name}' in cube '{self._cube.name}.")
            idx_member = dimensions[idx_dim]._member_idx_lookup[member_name]

            member_level = dimensions[idx_dim].member_defs[idx_member][self._cube._dimensions[0].LEVEL]
            return idx_dim, idx_member, member_level

        # No dimension identifier in member name, search all dimensions
        for idx_dim in range(self._cube.dimensions_count):
            if member_name in dimensions[idx_dim]._member_idx_lookup:
                idx_member = dimensions[idx_dim]._member_idx_lookup[member_name]
                # adjust the super_level
                member_level = dimensions[idx_dim].member_defs[idx_member][level]
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
                               f"address the same dimensions and the same number of member_defs, "
                               f"e.g.: a['Jan'] = a['Feb'] would be valid, but "
                               f"a['Jan'] = a['2022'] would not be valid, because of different dimensions.")

            if not self.identical_modifiers(self._modifiers, other._modifiers):
                self.clear()  # clear the target area

            if other._pinned:
                for record in other._pinned_records:
                    idx_address = record[0]

                    for modifier in self._modifiers:
                        idx_dim = modifier[0]
                        idx_member = modifier[2][0]
                        idx_address[idx_dim] = idx_member

                    # values = record[1]
                    # for key in values:
                    #     value = values[key]
                    #     if other._func:
                    #         value = other._func(value)
                    #     bolt = (0, tuple(idx_address), key)
                    #     self._cube._set(bolt, value)
                    #     # print(f"{idx_address} >>> {self._cube._idx_address_to_address(idx_address)}:= {value} is {self._cube._get(bolt)}")
                    value = record[1]
                    if other._func:
                        value = other._func(value)
                    bolt = (0, tuple(idx_address))
                    self._cube._set(bolt, value)

            else:
                if not other._rows:
                    other.refresh()
                other.refresh()

                facts = other._cube._facts
                for row in other._rows:
                    idx_address = list(facts.addresses[row])
                    for modifier in self._modifiers:
                        idx_dim = modifier[0]
                        idx_member = modifier[2][0]
                        idx_address[idx_dim] = idx_member

                    # for key in facts.facts[row]:
                    #     value = facts.facts[row][key]
                    #     if other._func:
                    #         value = other._func(value)
                    #     bolt = (0, tuple(idx_address), key)
                    #     self._cube._set(bolt, value)
                    #     # print(f"{idx_address} >>> {self._cube._idx_address_to_address(idx_address)}:= {value} is {self._cube._get(bolt)}")
                    value = facts.facts[row]
                    if other._func:
                        value = other._func(value)
                    bolt = (0, tuple(idx_address))
                    self._cube._set(bolt, value)


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
        if len(modifiers_a) == 0 or len(modifiers_b) == 0:
            return True
        elif len(modifiers_a) != len(modifiers_b):
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
