# -*- coding: utf-8 -*-
# Copyright (c) Thomas Zeutschler (Germany).
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import json
from collections.abc import Iterable
import collections.abc

from case_insensitive_dict import CaseInsensitiveDict
from custom_exceptions import *
import utils


class Dimension:
    """
    Dimensions contain a flat or hierarchical list of :ref:`members <members>`.
    Dimensions are used to define the axis of a multi-dimensional :ref:`cube <cubes>`.

    .. important::
        It is not foreseen to *Dimension* objects directly! Always use the ``add_dimension(...)``
        method of a database to create a new *Dimension* instance, as shown in the code fragment below.

        .. code:: python

            from tinyolap.database import Database

            # setup a new database
            database = Database("foo")

            # define dimensions
            dimension = db.add_dimension("bar")

    Within a single database, dimensions need to be unique by there name.
    """

    class MemberIndexManager:
        """
        Manages the available member index numbers.
        """
        def __init__(self, current: list[int] = None):
            self.free: set[int] = set()
            self.next_new = 1
            if current:
                all_members = set(range(max(current) + 1))
                used_members = set(current)
                self.free: all_members - used_members
                self.next_new = max(current) + 1

        def clear(self):
            self.free: set[int] = set()
            self.next_new = 1

        def pop(self) -> int:
            if self.free:
                return self.free.pop()
            index = self.next_new
            self.next_new += 1
            return index

        def push(self, index):
            if type(index) is int:
                self.free.add(index)
            elif isinstance(index, collections.abc.Sequence):
                self.free.update(index)
            else:
                raise ValueError()


    __magic_key = object()

    @classmethod
    def create(cls, backend, name: str, description: str = ""):
        dimension = Dimension(Dimension.__magic_key, name, description)
        dimension._backend = backend
        return dimension

    IDX = 0
    NAME = 1
    DESC = 2
    PARENTS = 3
    CHILDREN = 4
    ALL_PARENTS = 5
    LEVEL = 6
    ATTRIBUTES = 7
    BASE_CHILDREN = 8
    ALIAS = 9

    def __init__(self, dim_creation_key, name: str, description: str = ""):
        """
        NOT INTENDED FOR DIRECT USE! Cubes and dimensions always need to be managed by a Database.
        Use method 'Database.add_cube(...)' to create objects type Cube.

        :param dim_creation_key:
        :param name:
        :param description:
        """
        assert (dim_creation_key == Dimension.__magic_key), \
            "Objects of type Dimension can only be created through the method 'Database.add_dimension()'."

        self.name: str = name.strip()
        self.description: str = description
        self.members: dict[int, dict] = {}
        self._member_idx_manager = Dimension.MemberIndexManager()
        # self.member_idx_lookup: dict[str, int] = {}
        self.member_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self.attributes : CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self.subsets : CaseInsensitiveDict[str, tuple[int]] = CaseInsensitiveDict()
        self.member_counter = 0
        self.highest_idx = 0
        self.backend = None
        self.edit_mode: bool = False
        self.recovery_json = ""
        self.recovery_idx = set()
        self.database = None

    def __str__(self):
        """Returns the string representation of the dimension."""
        return f"dim:{self.name}"

    def __repr__(self):
        """Returns the string representation of the dimension."""
        return f"dim{self.name}"

    def __len__(self):
        """Returns the length (number of members) of the dimension"""
        return len(self.members)

    # region Dimension editing
    def clear(self) -> Dimension:
        """Deletes all members and all members from the dimension. Attributes will be kept."""
        self.member_idx_lookup = {}
        self.members = {}
        self._member_idx_manager.clear()
        self.member_counter = 0
        return self

    def edit(self) -> Dimension:
        """Sets the dimension into edit mode. Required to add, remove or rename members,
        to add remove or edit subsets or attributes and alike."""
        if self.edit_mode:
            raise DimensionEditModeException("Failed to set edit mode. 'edit_begin()' was already called before.")
        self.edit_mode = True
        self.recovery_json = self.to_json()
        self.recovery_idx = set(self.member_idx_lookup.values())
        return self

    def commit(self) -> Dimension:
        """Commits all changes since 'edit_begin()' was called and ends the edit mode."""
        self.__update_member_hierachies()
        if self.backend:
            self.backend.dimension_update(self, self.to_json())
        # remove data for obsolete members (if any) from database
        obsolete = self.recovery_idx.difference(set(self.member_idx_lookup.values()))
        if obsolete:
            self.database._remove_members(self, obsolete)
        self.edit_mode = False
        self.database._flush_cache()
        return self

    def rollback(self) -> Dimension:
        """Rollback all changes since 'edit_begin()' was called and ends the edit mode."""
        self.from_json(self.recovery_json)
        self.edit_mode = False
        return self

    # endregion

    # region add, remove, rename members
    def add_member(self, member, children=None, description=None):
        """Adds one or multiple members and (optionally) associated child-members to the dimension.
        :param member: A single string or an iterable of strings containing the members to be added.
        :param children: A single string or an iterable of strings containing the child members to be added.
        If parameter 'member' is an iterable of strings, then children must be an iterable of same size,
        either containing strings (adds a single child) or itself an iterable of string (adds multiple children).
        :param description: A description for the member to be added. If parameter 'member' is an iterable,
        then description will be ignored. For that case, please set descriptions for each member individually.
        """
        if not self.edit_mode:
            raise DimensionEditModeException("Failed to add member. Dimension is not in edit mode.")

        member_list = member
        children_list = children
        multi = False

        if isinstance(member, str):  # and (not isinstance(member, collections.abc.Sequence)):
            if not self.__valid_member_name(member):
                raise KeyError(f"Failed to add member. Invalid member name '{member}'. "
                                                 f"'\\t', '\\n' and '\\r' characters are not supported.")

            member_list = [member]
            children_list = [children]
            multi = True
        if not children:
            children_list = [None] * len(member_list)

        for m, c in zip(member_list, children_list):
            # add the member
            self.__member_add_parent_child(member=m, parent=None, description=(None if multi else description))

            if c:
                # add children
                if isinstance(c, str):
                    c = [c]
                elif not (isinstance(c, collections.abc.Sequence) and not isinstance(c, str)):
                    raise DimensionEditModeException(
                        f"Failed to member '{m}' to dimension '{self.name}'. Unexpected type "
                        f"'{type(c)}' of parameter 'children' found.")
                for child in c:
                    if not isinstance(child, str):
                        raise DimensionEditModeException(
                            f"Failed to add child to member '{m}' of dimension '{self.name}. Unexpected type "
                            f"'{type(c)}' of parameter 'children' found.")
                    if not self.__valid_member_name(child):
                        raise KeyError(f"Failed to add member. Invalid member name '{child}'. "
                                                         f"'\\t', '\\n' and '\\r' characters are not supported.")
                    self.__member_add_parent_child(member=child, parent=m, weight=1.0)

    def rename_member(self, member: str, new_name: str, new_description: str = None):
        """Renames a member."""
        if member not in self.member_idx_lookup:
            raise ValueError("Invalid or empty member name.")
        if not new_name:
            raise ValueError("Invalid or empty new member name.")
        if new_name == "*":
            raise ValueError("Invalid member new name. '*' is not a valid member name.")
        if new_name in self.members:
            raise ValueError("New name already exists.")

        idx_member = self.member_idx_lookup[member]
        self.members[idx_member][self.DESC] = (new_description if new_description else member)
        self.member_idx_lookup.pop(member)
        self.member_idx_lookup[new_name] = idx_member

    def remove_member(self, member):
        """Removes one or multiple members from a dimension."""
        member_list = member
        if isinstance(member, str):
            member_list = [member]

        # Ensure all members exist
        for member in member_list:
            if member not in self.member_idx_lookup:
                raise DimensionEditModeException(f"Failed to remove member(s). "
                                                 f"At least 1 of {len(member_list)} member ('{member}') is not "
                                                 f"a member of dimension {self.name}")

        # remove from directly related members
        for member in member_list:
            idx = self.member_idx_lookup[member]
            children = list(self.members[idx][self.CHILDREN])
            parents = list(self.members[idx][self.PARENTS])

            for child in children:
                if idx in self.members[child][self.PARENTS]:
                   self.members[child][self.PARENTS].remove(idx)
            for parent in parents:
                if idx in self.members[parent][self.CHILDREN]:
                    self.members[parent][self.CHILDREN].remove(idx)

        # remove from all related members
        for all_idx in self.member_idx_lookup.values():
            for member_idx in [self.member_idx_lookup[member] in member_list]:
                if member_idx in self.members[all_idx][self.ALL_PARENTS]:
                    self.members[all_idx][self.ALL_PARENTS].remove(member_idx)
                if member_idx in self.members[all_idx][self.BASE_CHILDREN]:
                    self.members[all_idx][self.BASE_CHILDREN].remove(member_idx)

        # finally remove the members
        member_idx_to_remove = [self.member_idx_lookup[m] for m in member_list]
        self._member_idx_manager.push(member_idx_to_remove)

        for m in member_list:
            del self.member_idx_lookup[m]
        for idx in member_idx_to_remove:
            if idx in self.members:
                del self.members[idx]
    # endregion


    # region member information functions
    def member_exists(self, member: str):
        """Check if a member is defined in the dimension."""
        return member in self.member_idx_lookup

    def member_get_index(self, member: str):
        """Returns the internal index of a member. RESERVED FOR FUTURE USE!"""
        if member not in self.member_idx_lookup:
            raise ValueError(f"A member named '{member}' is not defined in dimension'{self.name}'")
        return self.member_idx_lookup[member]

    def member_get_parents(self, member: str):
        """Returns all parents of a member."""
        if member not in self.member_idx_lookup:
            raise ValueError(f"A member named '{member}' is not defined in dimension'{self.name}'")
        return self.members[self.member_idx_lookup[member]][self.PARENTS]

    def member_get_children(self, member: str):
        """Returns all children of a member."""
        if member not in self.member_idx_lookup:
            raise ValueError(f"A member named '{member}' is not defined in dimension'{self.name}'")
        return [self.members[idx][self.NAME] for idx in self.members[self.member_idx_lookup[member]][self.CHILDREN]]

    def member_get_level(self, member: str):
        """Returns the level of a member within the member hierarchy.
        Value 0 identifies leave members, values greater 0 identify aggregated members."""
        if member not in self.member_idx_lookup:
            raise ValueError(f"A member named '{member}' is not defined in dimension'{self.name}'")
        return self.members[self.member_idx_lookup[member]][self.LEVEL]
    # endregion

    # region member enumeration functions (returning lists of members)
    def get_members(self) -> list[str]:
        """Returns all members of the dimension."""
        return list(self.member_idx_lookup.keys())

    def get_members_idx(self) -> list[int]:
        """Returns the index of all members of the dimension."""
        return list(self.member_idx_lookup.values())

    def get_members_by_level(self, level: int) -> list[str]:
        """Returns all members of a specific level."""
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] == level]

    def get_top_level(self) -> int:
        """Returns the highest member level over all members of the dimension."""
        return max([self.members[idx_member][self.LEVEL] for idx_member in self.members])

    def get_leave_members(self) -> list[str]:
        """Returns all leave members (members without children) of the dimension."""
        members = []
        for idx_member in self.members:
            if self.members[idx_member][self.LEVEL] == 0:
                members.append(self.members[idx_member][self.NAME])
        return members

    def get_aggregated_members(self) -> list[str]:
        """Returns all aggregated members (members with children) of the dimension."""
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] > 0]

    def get_root_members(self) -> list[str]:
        """Returns all root members (members with a parent) of the dimension."""
        members = []
        for idx_member in self.members:
            if not self.members[idx_member][self.PARENTS]:
                members.append(self.members[idx_member][self.NAME])
        return members
    # endregion

    # region attributes
    def set_attribute(self, member: str, attribute: str, value):
        """
        Sets an attribute for a specific member of the dimension.
        :param member: Name of the member to set the attribute for.
        :param attribute: Name of the attribute to be set.
        :param value: Value to be set.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :raises TypeError: Raised when the value if not of the expected type.
        """
        if attribute not in self.attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self.name}.")
        expected_type = self.attributes[attribute]
        if not type(value) is expected_type:
            raise TypeError(f"Failed to set attribute value. "
                           f"Type of value is '{str(type(value))}' but '{str(expected_type)}' was expected.")
        if member not in self.member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self.name}.")
        idx = self.member_idx_lookup[member]
        self.members[idx][self.ATTRIBUTES][attribute] = value

    def get_attribute(self, member: str, attribute: str):
        """
        Returns the attribute value for a specific member of the dimension.
        :param member: Name of the member to get the attribute for.
        :param attribute: Name of the attribute to be returned.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :return: The value of the attribute, or ``None`` if the attribute is not defined for the specific member.
        """
        if attribute not in self.attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self.name}.")
        if member not in self.member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self.name}.")
        idx = self.member_idx_lookup[member]
        if attribute not in self.members[idx][self.ATTRIBUTES]:
            return None
        return self.members[idx][self.ATTRIBUTES][attribute]

    def del_attribute(self, member: str, attribute: str):
        """
        Deletes an attribute value for a specific member of the dimension.
        :param member: Name of the member to delete the attribute for.
        :param attribute: Name of the attribute to be deleted.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        """
        if attribute not in self.attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self.name}.")
        if member not in self.member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self.name}.")
        idx = self.member_idx_lookup[member]
        if attribute in self.members[idx][self.ATTRIBUTES]:
            del(self.members[idx][self.ATTRIBUTES][attribute])

    def add_attribute(self, attribute_name: str, value_type: type = object):
        """
        Adds an attribute field to the dimension. Attributes enable to store additional information
        along side of dimension members. Attributes have a value_type which is checked when an attribute
        value is set.
        :param attribute_name: Name of the attribute to be added.
        :param value_type: Type of value expected for the attribute. Default value is ``object`` to allow any data.
        :raises InvalidKeyException: Raised when the name of the attribute is invalid.
        :raises DuplicateKeyException: Raised when the name of the attribute already exists.
        """
        if not utils.is_valid_db_object_name(attribute_name):
            raise InvalidKeyException(f"'{attribute_name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if attribute_name in self.attributes:
            raise DuplicateKeyException(f"Failed to add attribute to dimension. "
                                        f"A dimension attribute named '{attribute_name}' already exists.")
        self.attributes[attribute_name] = value_type

    def rename_attribute(self, attribute_name: str, new_attribute_name: str):
        """
        Renames an attribute of a dimension.
        :param attribute_name: The name of the attribute to be renamed.
        :param new_attribute_name: The new name of the attribute.
        :raises InvalidKeyException: Raised when the new name of the attribute is invalid.
        :raises DuplicateKeyException: Raised when the new name of the attribute already exists.
        """
        if not utils.is_valid_db_object_name(new_attribute_name):
            raise InvalidKeyException(f"Failed to rename dimension attribute. "
                                      f"'{new_attribute_name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if attribute_name not in self.attributes:
            raise KeyError(f"Failed to rename dimension attribute. "
                           f"A dimension attribute named '{attribute_name}' does not exist.")

        # add new , remove old attribute values
        for member in self.members.values():
            if attribute_name in member[self.ATTRIBUTES]:
                member[self.ATTRIBUTES][new_attribute_name] = member[self.ATTRIBUTES][attribute_name]
                del (member[self.ATTRIBUTES][attribute_name])

    def remove_attribute(self, attribute_name: str):
        """
        Removes an attribute from the dimension.
        :param attribute_name: Name of the attribute to be removed.
        :raises Raises KeyError if the attribute name not exists
        """
        if attribute_name not in self.attributes:
            raise KeyError(f"Failed to remove attribute from dimension. "
                           f"A dimension attribute named '{attribute_name}' does not exist.")
        # delete all values
        for member in self.members.values():
            if attribute_name in member[self.ATTRIBUTES]:
                del (member[self.ATTRIBUTES][attribute_name])
        del (self.attributes[attribute_name])

    def get_members_by_attribute(self, attribute_name: str, attribute_value) -> list[str]:
        """
        Returns all members having a specific attribute value.
        :param attribute_name: Name of the attribute to be analyzed.
        :param attribute_value: Value of the attribute to used for filtering.
        :return:
        """
        if attribute_name not in self.attributes:
            raise KeyError(f"Failed to return members by attribute. "
                           f"'{attribute_name}' is not an attribute of dimension {self.name}.")
        members = []
        for idx_member in self.members:
            if attribute_name in self.members[idx_member][self.ATTRIBUTES] == attribute_value:
                members.append(self.members[idx_member][self.NAME])
        return members

    # endregion

    # region serialization
    def to_json(self, beautify: bool = False):
        """Returns the json representation of the dimension."""
        data = ['{', f'"content": "dimension",', f'"name": "{self.name}",', f'"description": "{self.description}",',
                f'"count": {self.member_counter},', f'"members": {json.dumps(self.members)},',
                f'"lookup": {json.dumps(self.member_idx_lookup)},', f'"attributes": {json.dumps(self.attributes)},',
                f'"subsets": {json.dumps(self.subsets)}', '}']
        json_string = ''.join(data)
        if beautify:
            parsed = json.loads(json_string)
            json_string = json.dumps(parsed, indent=4)
        return json_string

    def from_json(self, json_string: str):
        """Initializes the dimension from json.
        WARNING, CALLING THIS METHOD ON DIMENSIONS WHICH ARE ALREADY
        USED BY CUBES CONTAINING DATA WILL CORRUPT YOUR DATABASE!"""
        if not self.edit_mode:
            self.edit()

        try:
            # first, read everything
            dim = json.loads(json_string)
            new_name = dim["name"]
            new_description = dim["description"]
            new_count = dim["count"]
            new_members = dim["members"]
            new_member_idx_lookup = dim["lookup"]
            new_attributes = dim["attributes"]
            new_subsets = dim["subsets"]

            # json does not allow non-string keys, but we use integer keys. Conversion is required.
            new_members = utils.dict_keys_to_int(new_members)

            # second, apply everything (this should not fail)
            self.name = new_name
            self.description = new_description
            self.member_counter = new_count
            self.members = new_members
            self.member_idx_lookup = new_member_idx_lookup
            self.attributes = new_attributes
            self.subsets = new_subsets
            self.commit()
        except Exception as err:
            raise FatalException(f"Failed to load json for dimension '{self.name}'. {str(err)}")

    # endregion

    # region auxiliary function to add, remove or rename members
    @staticmethod
    def __valid_member_name(name):
        return not(("\t" in name) or ("\n" in name) or ("\r" in name))

    def __member_add_parent_child(self, member, parent, weight: float = 1.0, description: str = None):
        if member in self.member_idx_lookup:
            member_idx = self.member_idx_lookup[member]
            if description:
                self.members[member_idx][self.DESC] = description
            if parent:
                self.__add_parent(member, parent)
        else:
            self.member_counter += 1
            # todo: Maintain more intelligent list of member index. Use the counter will fail
            # member_idx = self.member_counter
            member_idx = self._member_idx_manager.pop()
            self.member_idx_lookup[member] = member_idx
            self.members[member_idx] = {self.IDX: member_idx,
                                        self.NAME: member,
                                        self.DESC: (description if description else member),
                                        self.PARENTS: [],
                                        self.ALL_PARENTS: [],
                                        self.CHILDREN: [],
                                        self.LEVEL: 0,
                                        self.ATTRIBUTES: {},
                                        self.BASE_CHILDREN: []
                                        }

            if parent:
                self.__add_parent(member, parent)

    def __add_parent(self, member: str, parent: str = None):
        member_idx = self.member_idx_lookup[member]
        level = self.members[member_idx][self.LEVEL]
        if parent not in self.member_idx_lookup:
            # create parent member
            self.member_counter += 1
            parent_idx = self.member_counter
            self.member_idx_lookup[parent] = parent_idx
            self.members[parent_idx] = {self.IDX: parent_idx,
                                        self.NAME: parent,
                                        self.DESC: parent,
                                        self.PARENTS: [],
                                        self.ALL_PARENTS: [],
                                        self.CHILDREN: [member_idx],
                                        self.LEVEL: level + 1,
                                        self.ATTRIBUTES: {},
                                        self.BASE_CHILDREN: []
                                        }
        else:
            parent_idx = self.member_idx_lookup[parent]
            self.members[parent_idx][self.LEVEL] = level + 1
            if member_idx not in self.members[parent_idx][self.CHILDREN]:
                self.members[parent_idx][self.CHILDREN].append(member_idx)

        # add new parent to member
        if parent_idx not in self.members[member_idx][self.PARENTS]:
            self.members[member_idx][self.PARENTS].append(parent_idx)

        # update all-parents list, only relevant for base level members
        self.__update_all_parents(member_idx, parent_idx)

    def __update_all_parents(self, idx, parent_idx):
        if self.members[idx][self.LEVEL] > 0:
            for child_idx in self.members[idx][self.CHILDREN]:
                self.__update_all_parents(child_idx, parent_idx)
        else:
            if parent_idx not in self.members[idx][self.ALL_PARENTS]:
                self.members[idx][self.ALL_PARENTS].append(parent_idx)

    def __update_member_hierachies(self):
        for idx in self.member_idx_lookup.values():
            if self.members[idx][self.LEVEL] > 0:
                # update base level children
                self.members[idx][self.BASE_CHILDREN] = self.__get_base_members(idx)
            else:
                self.members[idx][self.ALL_PARENTS] = self.__get_all_parents(idx)

    def __get_all_parents(self, idx) -> list[int]:
        all_parents= []
        for parent in self.members[idx][self.PARENTS]:
            all_parents.append(parent)
            all_parents = all_parents + self.__get_all_parents(parent)
        return all_parents

    def __get_base_members(self, idx) -> list[int]:
        if self.members[idx][self.LEVEL] == 0:
            return [idx]
        else:
            base_members = []
            for child_idx in self.members[idx][self.CHILDREN]:
                if self.members[child_idx][self.LEVEL] == 0:
                    base_members.append(child_idx)
                else:
                    base_members.extend(self.__get_base_members(child_idx))
            return base_members
    # endregion
