# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in
# the LICENSE file in the root directory of this source tree.

from __future__ import annotations

import collections.abc
import json

from storage.storageprovider import StorageProvider
from tinyolap.member import Member
from tinyolap.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.exceptions import *
from tinyolap.utils import *


class Dimension:
    """
    Dimensions are used to define the axis of a multi-dimensional :ref:`cube <cubes>`.
    Dimensions contain a list or hierarchy of :ref:`members <members>`.
    Members are string address and representing the entities of the dimension. e.g.,
    for a dimension called 'months' this would be the month names 'Jan' to 'Dec' or
    month aggregations like quarters or semesters.

    .. important::
        It is not foreseen to create *Dimension* objects directly! Always use the ``add_dimension()``
        method of a :ref:`database <databases>` to create a new dimension instance,
        as shown in the code fragment below.

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

        def __init__(self, current: list[int] = None, first_free: int = 1):
            self.free: set[int] = set()
            self.next_new = max(1, first_free)
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
    def _create(cls, storage_provider: StorageProvider, name: str, description: str = ""):
        """
        NOT INTENDED FOR EXTERNAL USE! Creates a new dimension.

        :param storage_provider: The storage provider of the database.
        :param name: Name of the dimension to be created.
        :param description: Description of the dimension to be added.
        :return: The new dimension.
        """
        dimension = Dimension(Dimension.__magic_key, name, description)
        dimension._storage_provider = storage_provider
        if storage_provider and storage_provider.connected:
            storage_provider.add_dimension(name, dimension.to_json())
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
    ALIASES = 9
    FORMAT = 10

    MEMBERS = 3
    IDX_MEMBERS = 4

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
        self._member_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self._member_idx_list = []
        self.member_counter = 0
        self.highest_idx = 0

        self.database = None
        self._storage_provider: StorageProvider = None
        self.edit_mode: bool = False
        self.recovery_json = ""
        self.recovery_idx = set()

        self.alias_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self.attributes: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self.attribute_query_caching: bool = True
        self.attribute_cache: CaseInsensitiveDict[str, list[str]] = CaseInsensitiveDict()
        self.subsets: CaseInsensitiveDict[str, dict] = CaseInsensitiveDict()
        self._subset_idx_manager = Dimension.MemberIndexManager()

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
        """
        Deletes all members and all members from the dimension. Attributes will be kept.

        :return: The dimension itself.
        """
        self._member_idx_lookup = CaseInsensitiveDict()
        self.members = {}
        self._member_idx_manager.clear()
        self.alias_idx_lookup.clear()
        self.member_counter = 0
        self.subsets = {}
        self._subset_idx_manager.clear()
        return self

    def edit(self) -> Dimension:
        """
        Sets the dimension into edit mode. Required to add, remove or rename members,
        to add remove or edit subsets or attributes and alike.

        :return: The dimension itself.
        """
        if self.edit_mode:
            raise DimensionEditModeException("Failed to set edit mode. 'edit_begin()' was already called before.")
        self.edit_mode = True
        self.recovery_json = self.to_json()
        self.recovery_idx = set(self._member_idx_lookup.values())
        return self

    def commit(self) -> Dimension:
        """
        Commits all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        self.__update_member_hierarchies()
        if self._storage_provider and self._storage_provider.connected:
            self._storage_provider.add_dimension(self.name, self.to_json())

        # remove data for obsolete members (if any) from database
        obsolete = self.recovery_idx.difference(set(self._member_idx_lookup.values()))
        if obsolete:
            self.database._remove_members(self, obsolete)
        # update member list
        self._member_idx_list = [idx for idx in self.members.keys()]

        self.edit_mode = False
        self.database._flush_cache()
        return self

    def rollback(self) -> Dimension:
        """
        Rollback all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        self.from_json(self.recovery_json)
        self.edit_mode = False
        return self

    # endregion

    # region member context
    def member(self, member) -> Member:
        if type(member) is int:
            try:
                member_name = self.members[member]
                return Member(self, member_name,
                              None, idx_dim=-1,
                              idx_member=member,
                              member_level=self.members[self._member_idx_lookup[member_name]][self.LEVEL])
            except (IndexError, ValueError):
                raise KeyError(f"Failed to return Member with index '{member}'. The member does not exist.")

        elif member in self._member_idx_lookup:
            idx_member = self._member_idx_lookup[member]
            return Member(self, member,
                          None, idx_dim=-1,
                          idx_member=idx_member,
                          member_level=self.members[self._member_idx_lookup[member]][self.LEVEL])
        raise KeyError(f"Failed to return Member '{member}'. The member does not exist.")

    # region add, remove, rename members
    def add_member(self, member, children=None, description=None, number_format=None) -> Dimension:
        """Adds one or multiple members and (optionally) associated child-members to the dimension.

        :param member: A single string or an iterable of strings containing the members to be added.
        :param children: A single string or an iterable of strings containing the child members to be added.
               If parameter 'member' is an iterable of strings, then children must be an iterable of same size,
               either containing strings (adds a single child) or itself an iterable of string (adds multiple children).
        :param description: A description for the member to be added. If parameter 'member' is an iterable,
               then description will be ignored. For that case, please set descriptions for each member individually.
        :param number_format: A format string for output formatting, e.g. for numbers or percentages.
               Formatting follows the standard Python formatting specification at
               <https://docs.python.org/3/library/string.html#format-specification-mini-language>.
        :return Dimension: Returns the dimension itself.
        """
        if not self.edit_mode:
            raise DimensionEditModeException("Failed to add member. Dimension is not in edit mode.")

        member_list = member
        children_list = children
        multi = False

        if isinstance(member, str):
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
            idx_member = self.__member_add_parent_child(member=m, parent=None,
                                                        description=(None if multi else description))
            if number_format:
                self.members[idx_member][self.FORMAT] = number_format

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

        return self

    def rename_member(self, member: str, new_name: str, new_description: str = None):
        """Renames a member."""
        if member not in self._member_idx_lookup:
            raise ValueError("Invalid or empty member name.")
        if not new_name:
            raise ValueError("Invalid or empty new member name.")
        if new_name == "*":
            raise ValueError("Invalid member new name. '*' is not a valid member name.")
        if new_name in self.members:
            raise ValueError("New name already exists.")

        idx_member = self._member_idx_lookup[member]
        self.members[idx_member][self.DESC] = (new_description if new_description else member)
        self._member_idx_lookup.pop(member)
        self._member_idx_lookup[new_name] = idx_member

        # adjust subsets
        for subset in self.subsets:
            if member in subset[self.MEMBERS]:
                idx = subset[self.MEMBERS].index(member)
                subset[self.MEMBERS][idx] = new_name

    def remove_member(self, member):
        """
        Removes one or multiple members from a dimension.

        :param member: The member or an iterable of members to be deleted.
        """
        member_list = member
        if isinstance(member, str):
            member_list = [member]

        # Ensure all members exist
        for member in member_list:
            if member not in self._member_idx_lookup:
                raise DimensionEditModeException(f"Failed to remove member(s). "
                                             f"At least 1 of {len(member_list)} member ('{member}') is not "
                                             f"a member of dimension {self.name}")

        # remove from directly related members
        for member in member_list:
            idx = self._member_idx_lookup[member]
            children = list(self.members[idx][self.CHILDREN])
            parents = list(self.members[idx][self.PARENTS])

            for child in children:
                if idx in self.members[child][self.PARENTS]:
                    self.members[child][self.PARENTS].remove(idx)
            for parent in parents:
                if idx in self.members[parent][self.CHILDREN]:
                    self.members[parent][self.CHILDREN].remove(idx)

        # remove from all related members
        for all_idx in self._member_idx_lookup.values():
            for member_idx in [self._member_idx_lookup[member] in member_list]:
                if member_idx in self.members[all_idx][self.ALL_PARENTS]:
                    self.members[all_idx][self.ALL_PARENTS].remove(member_idx)
                if member_idx in self.members[all_idx][self.BASE_CHILDREN]:
                    self.members[all_idx][self.BASE_CHILDREN].remove(member_idx)

        # remove the members
        member_idx_to_remove = [self._member_idx_lookup[m] for m in member_list]
        self._member_idx_manager.push(member_idx_to_remove)

        for m in member_list:
            del self._member_idx_lookup[m]
        for idx in member_idx_to_remove:
            if idx in self.members:
                del self.members[idx]

        # adjust subsets
        for subset in self.subsets.values():
            members_to_remove = set(member_list).intersection(set(subset[self.MEMBERS]))
            if members_to_remove:
                for member in members_to_remove:
                    idx = subset[self.MEMBERS].index(member)
                    subset[self.MEMBERS].pop(idx)
                    subset[self.IDX_MEMBERS].pop(idx)

    # endregion

    # region member aliases
    def member_add_alias(self, member: str, alias: str):
        """
        Adds a member alias to the dimension. Aliases enable the access of members
        by alternative names or address (e.g. a technical key, or an abbreviation).

        :param member: Name of the member to add an alias for.
        :param alias: The alias to be set.
        :raises KeyError: Raised if the member does not exist.
        :raises DuplicateKeyException: Raised if the alias is already used by another member.
                Individual aliases can only be assigned to one member.

        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not member a of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        if alias in self.alias_idx_lookup:
            raise DuplicateKeyException(f"Duplicate alias. The alias '{alias}' is already used "
                                    f"by member '{self.members[idx_member][self.NAME]}' of dimension'{self.name}'")
        self.alias_idx_lookup[alias] = idx_member

    def remove_alias(self, alias: str):
        """
        Removes a member alias from the dimension.

        :param alias: The alias to be removed.
        """
        if alias not in self.alias_idx_lookup:
            raise KeyError(f"{alias}' is not alias a of dimension'{self.name}'")
        del self.alias_idx_lookup[alias]

    def member_remove_all_aliases(self, member: str):
        """
        Removes all aliases of a member from the dimension.

        :param member: Name of the member to remove the aliases for.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not member a of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        aliases_to_be_deleted = set([key for key, idx in self.alias_idx_lookup.items() if idx == idx_member])
        for alias in aliases_to_be_deleted:
            del self.alias_idx_lookup[alias]

    def member_has_alias(self, member: str) -> bool:
        """
        Checks if for a given member an alias is defined.

        :param member: Name of the member to be checked.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        return idx_member in set(self.alias_idx_lookup.values())

    def member_aliases_count(self, member: str) -> int:
        """
        Returns the number of aliases defined for a given member.

        :param member: Name of the member to be checked.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to return member alias count. '{member}' is not a member of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        return len(set([idx for idx in set(self.alias_idx_lookup.values()) if idx == idx_member]))

    def get_member_by_alias(self, alias: str) -> str:
        """
        Returns the name of a member associated with the given.

        :param alias: Name of the alias to be checked.
        :raises KeyError: Raised if the alias does not exist.
        """
        if alias not in self.alias_idx_lookup:
            raise KeyError(f"Failed to get member by alias. '{alias}' is not a member alias of dimension'{self.name}'")
        idx_member = self.alias_idx_lookup[alias]
        return self.members[idx_member][self.NAME]

    # endregion

    # region member number_format (for output formatting)
    def member_set_format(self, member: str, format_string: str):
        """
        Set a number_format string for output formatting, especially useful for number formatting.
        Member formatting follows the standard Python formatting specification at
        https://docs.python.org/3/library/string.html#format-specification-mini-language.

        :param member: Name of the member to set the number_format for.
        :param format_string: The number_format string to be used. Member formatting follows the standard
               Python formatting specification at
               https://docs.python.org/3/library/string.html#format-specification-mini-language.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set member number_format. '{member}' is not a member of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        self.members[idx_member][self.FORMAT] = format_string

    def member_get_format(self, member: str) -> str:
        """
        Returns the number_format string of a member.

        :param member: Name of the member to return the number_format for.
        :return: Returns the number_format string for the member, or ``None`` if no number_format string is defined.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to return member number_format. '{member}' is not a member of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        return self.members[idx_member][self.FORMAT]

    def member_remove_format(self, member: str):
        """
        Removes the number_format string of a member.

        :param member: Name of the member to remove the number_format for.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to remove member number_format. '{member}' is not a member of dimension'{self.name}'")
        idx_member = self._member_idx_lookup[member]
        self.members[idx_member][self.FORMAT] = None

    # endregion

    # region member information functions
    def member_get_ordinal(self, member: str) -> int:
        """
        Returns the ordinal position of a member with the list of members of the dimension.

        :param member: Name of the member to be checked.
        :return: The ordinal position of the member. If the member does not exits -1 will be returned
        """
        if member in self._member_idx_lookup:
            return list(self._member_idx_lookup.keys()).index(member)
        return -1

    def member_exists(self, member: str) -> bool:
        """
        Check if the member exists in the dimension.

        :param member: Name of the member to be checked.
        :return: ``True`` if the member exists, ``False`` otherwise.
        """
        return member in self._member_idx_lookup

    def member_get_index(self, member: str) -> int:
        """
        Returns the database internal index of a member.

        :param member: Name of the member to be evaluated.
        :return: The internal index of the member.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self.name}'")
        return self._member_idx_lookup[member]

    def member_get_parents(self, member: str) -> list[str]:
        """
        Returns a list of all parents of a member.
        :param member: Name of the member to be evaluated.
        :return: List of parents.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self.name}'")
        parents = []
        for idx in self.members[self._member_idx_lookup[member]][self.PARENTS]:
            parents.append(self.members[idx][self.NAME])
        return parents

    def member_get_children(self, member: str):
        """
        Returns a list of all children of a member.

        :param member: Name of the member to be evaluated.
        :return: List of children.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self.name}'")
        children = []
        for idx in self.members[self._member_idx_lookup[member]][self.CHILDREN]:
            children.append(self.members[idx][self.NAME])
        return children

    def member_get_leave_children(self, member: str):
        """
        Returns a list of all leave (base level) children (or grand children) of a member.

        :param member: Name of the member to be evaluated.
        :return: List of children.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self.name}'")
        if self.members[self._member_idx_lookup[member]][self.LEVEL] == 0:
            # already a base member, return that
            return [member, ]
        children = []
        for idx in self.members[self._member_idx_lookup[member]][self.CHILDREN]:
            if self.members[idx][self.LEVEL] > 0:
                members = self.member_get_leave_children(self.members[idx][self.NAME])
                children.extend(members)
            else:
                children.append(self.members[idx][self.NAME])
        return children


    def member_get_level(self, member: str):
        """
        Returns the level of a member within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: 0 for leave level members, values > 0 for aggregated members.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self.name}'")
        return self.members[self._member_idx_lookup[member]][self.LEVEL]

    # endregion

    # region member enumeration functions (returning lists of members)
    def get_members(self) -> list[str]:
        """
        Returns a list of all members of the dimension.

        :return: List of all members of the dimension.
        """
        return list(self.members[idx][self.NAME] for idx in self._member_idx_lookup.values())
        # return list(str(key) for key in self._member_idx_lookup.keys())

    def get_members_idx(self) -> list[int]:
        """
        Returns a list of indexes of all members of the dimension.

        :return: List of indexes of all members of the dimension.
        """
        return list(self._member_idx_lookup.values())

    def get_members_by_level(self, level: int) -> list[str]:
        """
        Returns a list of all members of the specific member level. 0 identifies the leave level of the dimension.

        :param level: Level of the members to be returned.
        :return: List of members of the specific member level.
        """
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] == level]

    def get_top_level(self) -> int:
        """
        Returns the highest member level over all members of the dimension.

        :return: The highest member level over all members of the dimension.
        """
        return max([self.members[idx_member][self.LEVEL] for idx_member in self.members])

    def get_leave_members(self) -> list[str]:
        """
        Returns a list of all leave members (members without children = level equals 0) of the dimension.

        :return: List of leave level members of the dimension.
        """
        members = []
        for idx_member in self.members:
            if self.members[idx_member][self.LEVEL] == 0:
                members.append(self.members[idx_member][self.NAME])
        return members

    def get_aggregated_members(self) -> list[str]:
        """
        Returns a list of all aggregated members (members with children = level greater 0) of the dimension.

        :return: List of aggregated members of the dimension.
        """
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] > 0]

    def get_root_members(self) -> list[str]:
        """
        Returns a list of all root members (members with a parent) of the dimension.

        :return: Returns a list of all root members of the dimension.
        """
        members = []
        for idx_member in self.members:
            if not self.members[idx_member][self.PARENTS]:
                members.append(self.members[idx_member][self.NAME])
        return members

    def get_first_member(self) -> str:
        """
        Returns the first member of the dimension.

        :return: Returns the first members of the dimension.
        """
        for idx_member in self.members:
            return self.members[idx_member][self.NAME]
        return None

    # endregion

    # region attributes
    def attributes_count(self) -> int:
        """
        Returns the number attributes defined in the dimension.

        :return: Number attributes defined in the dimension.
        """
        return len(self.attributes)

    def set_attribute(self, attribute: str, member: str, value):
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
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self.name}.")
        idx = self._member_idx_lookup[member]
        self.members[idx][self.ATTRIBUTES][attribute] = value

        if self.attribute_query_caching:
            key = attribute + ":" + str(value)
            if key in self.attribute_cache:
                del self.attribute_cache[key]

    def get_attribute(self, attribute: str, member: str):
        """
        Returns the attribute value for a specific member of the dimension.

        :param attribute: Name of the attribute to be returned.
        :param member: Name of the member to get the attribute for.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :return: The value of the attribute, or ``None`` if the attribute is not defined for the specific member.
        """
        if attribute not in self.attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self.name}.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self.name}.")
        idx = self._member_idx_lookup[member]
        if attribute not in self.members[idx][self.ATTRIBUTES]:
            return None
        return self.members[idx][self.ATTRIBUTES][attribute]

    def get_attribute_type(self, attribute: str):
        """
        Returns the data type of an attribute.

        :param attribute: Name of the attribute to be returned.
        :raises KeyError: Raised when the attribute name does not exist.
        :return: The type of the attribute.
        """
        if attribute not in self.attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self.name}.")
        return self.attributes[attribute]

    def has_attribute(self, attribute: str):
        """
        Checks if a specific attribute is defined for the dimension.

        :param attribute: Name of the attribute to be checked.
        :return: ``True``if the attribute exists. ``False`` otherwise.
        """
        return attribute in self.attributes

    def del_attribute_value(self, attribute: str, member: str):
        """
        Deletes an attribute value for a specific member of the dimension.

        :param attribute: Name of the attribute to be deleted.
        :param member: Name of the member to delete the attribute for.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        """
        if attribute not in self.attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self.name}.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self.name}.")
        idx = self._member_idx_lookup[member]
        if attribute in self.members[idx][self.ATTRIBUTES]:
            del (self.members[idx][self.ATTRIBUTES][attribute])

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
        if not is_valid_db_object_name(attribute_name):
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
        if not is_valid_db_object_name(new_attribute_name):
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
        :raises KeyError: Raises KeyError if the attribute name not exists.

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
        if self.attribute_query_caching:
            key = attribute_name + ":" + str(attribute_value)
            if key in self.attribute_cache:
                return self.attribute_cache[key]

        if attribute_name not in self.attributes:
            raise KeyError(f"Failed to return members by attribute. "
                           f"'{attribute_name}' is not an attribute of dimension {self.name}.")
        members = []
        for idx_member in self.members:
            if attribute_name in self.members[idx_member][self.ATTRIBUTES]:
                if self.members[idx_member][self.ATTRIBUTES][attribute_name] == attribute_value:
                    members.append(self.members[idx_member][self.NAME])
        if self.attribute_query_caching:
            key = attribute_name + ":" + str(attribute_value)
            self.attribute_cache[key] = members
        return members

    # endregion

    # region subsets
    def add_subset(self, subset_name: str, members):
        """
        Adds a new subset to the dimension. A subset is a plain list of members,
        useful for calculation and reporting purposes.

        :param subset_name: Name of the subset to be added.
        :param members: A list (iterable) containing the member to be added to the subset.
        :raises InvalidKeyException: Raised when the name of the subset is invalid.
        :raises DuplicateKeyException: Raised when the name of the subset already exists.
        :raises TypeError: Raised when members list is not of the expected type (list or tuple)
        :raises KeyError: Raised when a member from the members list is not contained in the dimension.
        """
        if not is_valid_db_object_name(subset_name):
            raise InvalidKeyException(f"'{subset_name}' is not a valid dimension subset name. "
                                  f"Lower case alphanumeric characters and underscore supported only, "
                                  f"no whitespaces, no special characters.")
        if subset_name in self.subsets:
            raise DuplicateKeyException(f"Failed to add subset to dimension. "
                                    f"A dimension subset named '{subset_name}' already exists.")

        # validate members list
        if not ((type(members) is list) or (type(members) is tuple)):
            raise TypeError(f"Failed to add members to subset '{subset_name}'. "
                            f"Argument 'members' is not of expected type list or tuple, "
                            f"but of type '{type(subset_name)}'.")
        idx_members = []
        for member in members:
            if member in self._member_idx_lookup:
                idx_members.append(self._member_idx_lookup[member])
            else:
                raise KeyError(f"Failed to add member to subset. "
                               f"'{member}' is not a member of dimension {self.name}.")

        # create and add subset
        self.subsets[subset_name] = {self.IDX: self._subset_idx_manager.pop(),
                                     self.NAME: subset_name,
                                     self.MEMBERS: list(members),
                                     self.IDX_MEMBERS: idx_members}

    def has_subset(self, subset_name: str) -> bool:
        """
        Checks if a specific subset is defined for the dimension.

        :param subset_name: Name of the subset to be checked.
        :return: ``True``if the subset exists. ``False`` otherwise.
        """
        return subset_name in self.subsets

    def subsets_count(self) -> int:
        """
        Returns the number subsets defined in the dimension.

        :return: Number subsets defined in the dimension.
        """
        return len(self.subsets)

    def subset_contains(self, subset_name: str, member_name: str) -> bool:
        """
        Checks if a specific member is contained in a subset of the dimension.

        :param subset_name: Name of the subset to be checked.
        :param member_name: Name of the member to be checked.
        :return: ``True``if the member is contained in the subset. ``False`` otherwise.
        """
        if not subset_name in self.subsets:
            raise KeyError(f"Failed to check member contained in subset. "
                           f"'{subset_name}' is not a subset of dimension {self.name}.")
        return member_name in self.subsets[subset_name][self.MEMBERS]

    def rename_subset(self, subset_name: str, new_subset_name: str):
        """
        Renames a subset of the dimension.

        :param subset_name: Name of the subset to be added.
        :param new_subset_name: New name of the subset.
        :raises InvalidKeyException: Raised when the new name for the subset is invalid.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if not is_valid_db_object_name(new_subset_name):
            raise InvalidKeyException(f"'{new_subset_name}' is not a valid dimension subset name. "
                                  f"Lower case alphanumeric characters and underscore supported only, "
                                  f"no whitespaces, no special characters.")
        if not subset_name in self.subsets:
            raise KeyError(f"Failed to rename subset. "
                           f"'{subset_name}' is not a subset of dimension {self.name}.")

        subset = self.subsets[subset_name]
        del self.subsets[subset_name]
        self.subsets[new_subset_name] = subset

    def get_subset(self, subset_name: str) -> tuple[str]:
        """
        Returns the list of member from a subset to the dimension.

        :param subset_name: Name of the subset to be return.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if subset_name in self.subsets:
            return self.subsets[subset_name][self.MEMBERS]

        raise KeyError(f"Failed to return list of subset member. "
                       f"'{subset_name}' is not a subset of dimension {self.name}.")

    def remove_subset(self, subset_name: str):
        """
        Removes a subset from the dimension.

        :param subset_name: Name of the subset to be removed.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if subset_name in self.subsets:
            self._subset_idx_manager.push(self.subsets[subset_name][self.IDX])
            del (self.subsets[subset_name])
            return

        raise KeyError(f"Failed to remove subset. "
                       f"'{subset_name}' is not a subset of dimension {self.name}.")

    # endregion

    # region serialization
    def to_json(self, beautify: bool = False):
        """
        Returns the json representation of the dimension. Helpful for serialization
        and deserialization of a dimension. The json returned by this function is
        the same as the one contained in the SQLite database storage provider (if available).

        :param beautify: Identifies if the json code should be beautified (multiple rows + indentation).
        :return: A json string representing the dimension.
        """
        data = ['{', f'"content": "dimension",', f'"name": "{self.name}",', f'"description": "{self.description}",',
                f'"count": {self.member_counter},', f'"members": {json.dumps(self.members)},',
                f'"lookup": {json.dumps(self._member_idx_lookup)},', f'"attributes": {json.dumps(self.attributes)},',
                f'"subsets": {json.dumps(self.subsets)}', '}']
        json_string = ''.join(data)
        if beautify:
            parsed = json.loads(json_string)
            json_string = json.dumps(parsed, indent=4)
        return json_string

    def from_json(self, json_string: str):
        """
        (Re-)initializes the dimension from a json string.

        .. warning::
            Calling this method for dimensions which are already used by cubes
            will very likely **corrupt your database!** Calling this method is only save
            **before** you create any cube. Handle with care.

        :param json_string: The json string containing the dimension definition.
        :raises FatalException: Raised if an error occurred during the deserialization from json string.
        """
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

            # json does not allow non-string address, but we use integer address. Conversion is required.
            new_members = dict_keys_to_int(new_members)

            # second, apply everything (this should not fail)
            self.name = new_name
            self.description = new_description
            self.member_counter = new_count
            self.members = new_members
            self._member_idx_lookup = CaseInsensitiveDict().populate(new_member_idx_lookup)
            self.attributes = new_attributes
            self.subsets = new_subsets
            self.commit()
        except Exception as err:
            raise FatalException(f"Failed to load json for dimension '{self.name}'. {str(err)}")

    # endregion

    # region auxiliary function to add, remove or rename members
    @staticmethod
    def __valid_member_name(name):
        return not (("\t" in name) or ("\n" in name) or ("\r" in name))

    def __member_add_parent_child(self, member, parent, weight: float = 1.0, description: str = None) -> int:
        if member in self._member_idx_lookup:
            member_idx = self._member_idx_lookup[member]
            if description:
                self.members[member_idx][self.DESC] = description
            if parent:
                self.__add_parent(member, parent)
        else:
            self.member_counter += 1
            member_idx = self._member_idx_manager.pop()
            self._member_idx_lookup[member] = member_idx
            self.members[member_idx] = {self.IDX: member_idx,
                                        self.NAME: member,
                                        self.DESC: (description if description else member),
                                        self.PARENTS: [],
                                        self.ALL_PARENTS: [],
                                        self.CHILDREN: [],
                                        self.LEVEL: 0,
                                        self.ATTRIBUTES: {},
                                        self.BASE_CHILDREN: [],
                                        self.ALIASES: [],
                                        self.FORMAT: None,
                                        }

            if parent:
                self.__add_parent(member, parent)
        return member_idx

    def __add_parent(self, member: str, parent: str = None):
        member_idx = self._member_idx_lookup[member]
        level = self.members[member_idx][self.LEVEL]
        if parent not in self._member_idx_lookup:
            # create parent member
            self.member_counter += 1
            parent_idx = self.member_counter
            self._member_idx_lookup[parent] = parent_idx
            self.members[parent_idx] = {self.IDX: parent_idx,
                                        self.NAME: parent,
                                        self.DESC: parent,
                                        self.PARENTS: [],
                                        self.ALL_PARENTS: [],
                                        self.CHILDREN: [member_idx],
                                        self.LEVEL: level + 1,
                                        self.ATTRIBUTES: {},
                                        self.BASE_CHILDREN: [],
                                        self.ALIASES: [],
                                        self.FORMAT: None,
                                        }
        else:
            parent_idx = self._member_idx_lookup[parent]
            self.members[parent_idx][self.LEVEL] = level + 1
            if member_idx not in self.members[parent_idx][self.CHILDREN]:
                self.members[parent_idx][self.CHILDREN].append(member_idx)

        # add new parent to member
        if parent_idx not in self.members[member_idx][self.PARENTS]:
            self.members[member_idx][self.PARENTS].append(parent_idx)

        # check for circular references
        if self.__circular_reference_detection(member_idx, member_idx):
            # remove the relationship
            self.members[member_idx][self.PARENTS].remove(parent_idx)
            self.members[parent_idx][self.CHILDREN].remove(member_idx)

            raise DimensionEditModeException(f"Circular reference detected on adding parent <-> child relation "
                                         f"'{self.members[parent_idx][self.NAME]}' <-> "
                                         f"'{self.members[member_idx][self.NAME]}' "
                                         f"to dimension {self.name}. Both members were added, "
                                         f"but the relation was not created.")

        # update all-parents list, only relevant for base level members
        self.__update_all_parents(member_idx, parent_idx)

    def __update_all_parents(self, idx, parent_idx):
        if self.members[idx][self.LEVEL] > 0:
            for child_idx in self.members[idx][self.CHILDREN]:
                self.__update_all_parents(child_idx, parent_idx)
        else:
            if parent_idx not in self.members[idx][self.ALL_PARENTS]:
                self.members[idx][self.ALL_PARENTS].append(parent_idx)

    def __update_member_hierarchies(self):
        for idx in self._member_idx_lookup.values():
            if self.members[idx][self.LEVEL] > 0:
                # update base level children
                self.members[idx][self.BASE_CHILDREN] = self.__get_base_members(idx)
            else:
                self.members[idx][self.ALL_PARENTS] = self.__get_all_parents(idx)

    def __check_circular_reference(self):
        for idx in self._member_idx_lookup.values():
            if self.__circular_reference_detection(idx, idx):
                raise DimensionEditModeException(f"Failed to commit dimension. Circular reference detected "
                                             f"for member {self.members[idx][self.NAME]}.")

    def __circular_reference_detection(self, start: int, current: int, visited=None):
        if visited is None:
            visited = set()

        if current in visited:
            return True

        visited.add(current)
        for parent in self.members[current][self.PARENTS]:
            if self.__circular_reference_detection(current, parent, visited):
                return True
        visited.remove(current)
        return False

    def __get_all_parents(self, idx) -> list[int]:
        all_parents = []
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
