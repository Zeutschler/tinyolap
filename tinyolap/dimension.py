# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in
# the LICENSE file in the root directory of this source tree.

from __future__ import annotations
import importlib
import warnings
from collections.abc import Iterable, Sequence
import inspect
from abc import ABC, abstractmethod
import fnmatch
import json
from abc import abstractmethod
from enum import Enum
import enum_tools.documentation
from typing import Any

from tinyolap.config import Config
from tinyolap.storage.storageprovider import StorageProvider
from tinyolap.member import Member, MemberList
from tinyolap.exceptions import *
from tinyolap.utilities.utils import *
from tinyolap.utilities.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.utilities.hybrid_dict import HybridDict
from tinyolap.attributes import AttributeField, Attributes
from tinyolap.subsets import Subset, Subsets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tinyolap.database import Database

enum_tools.documentation.INTERACTIVE = True


@enum_tools.documentation.document_enum
class DimensionType(Enum):
    """Defines the type of dimension. Relevant for reporting purposes ."""
    GENERIC = 0     # doc: (default) Generic dimension with unspecified content.
    YEAR = 1        # doc: Dimension containing years, e.g., 2022, 2023, 2024...
    PERIOD = 2      # doc: Dimension containing periods of a year, most often months, weeks or days
    TIME = 3        # doc: Dimension contain time of a day, most often hours, minutes, seconds
    DATATYPE = 4    # doc: Dimension containing datatypes, e.g. Actual, Plan, Forecast etc.
    ENTITY = 5      # doc: Dimension containing entities, most often companies, legal entities
    GEOGRAPHIC = 6  # doc: Dimension containing geographic information, most often regions, countries
    PRODUCT = 7     # doc: Dimension containing products or services
    CUSTOMER = 8    # doc: Dimension containing customers
    SUPPLIER = 9    # doc: Dimension containing suppliers
    PERSON = 10      # doc: Dimension containing persons, most often employees, users


class Dimension:
    """
    Dimensions are used to define the axis of a multi-dimensional :ref:`cube <cubes>`.
    Dimensions contain a list or hierarchy of :ref:`member_defs <member_defs>`.
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
    __slots__ = '_name', '_description','_dimension_type', 'member_defs','_member_idx_manager',\
                '_member_idx_lookup','_member_idx_list', 'member_counter','highest_idx', '_members',\
                '_is_weighted', '_weights','_default_member', '_database', '_storage_provider', \
                '_edit_mode','_recovery_json', '_recovery_idx','alias_idx_lookup',\
                '_attributes', '_subsets'

    class MemberIndexManager:
        """
        Manages the available member index numbers.
        """
        __slots__ = 'free', 'next_new'

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
            elif isinstance(index, Sequence):
                self.free.update(index)
            else:
                raise ValueError()

    class DimensionWeightManager:
        """Manages weight information for aggregations of base level members."""
        __slots__ = 'is_weighted_dimension', 'dimension', 'weight_lookup'

        def __init__(self, dimension: Dimension, refresh: bool = False):
            self.is_weighted_dimension = False
            self.dimension = dimension
            self.weight_lookup = dict()
            if refresh:
                self.refresh()

        def get_parent_weightings(self, parent_idx: int):
            weights = self.weight_lookup.get(parent_idx, default=dict())
            return bool(weights), weights

        def refresh(self):
            """Refreshes the weight manager based on the current members of the dimension."""
            self.is_weighted_dimension = False
            # we only need to process aggregated members!
            # Travers each aggregated member down to their leaves.
            weight_lookups = dict()
            for parent in self.dimension.aggregated_members:
                weighted_leaves = self.get_weighted_leaves(parent, 1.0)
                # are there any leave members that has a non default weighting.
                # if NO, the current parent (and its dimension) does not require weighted aggregation
                # if YES, we need to keep these leave members to, lookup their weight while aggregation
                if weighted_leaves:
                    weight_lookups[parent.index] = weighted_leaves

            # if there is at least one weighted parent in the dimension
            # then the dimension requires weighted aggregation.
            self.weight_lookup = weight_lookups
            if weight_lookups:
                self.is_weighted_dimension = True

        def get_weighted_leaves(self, member: Member, base_weight: float = 1.0) -> dict[int, float]:
            """Returns all weighted leaves from a parent member."""
            weighted_leaves = {}
            for child in member.children:
                weight = child.parent_weight(member)
                if child.is_parent:
                    # merge results
                    weighted_leaves = {**weighted_leaves, **self.get_weighted_leaves(child, base_weight * weight)}
                else:
                    # add child and its weight
                    if base_weight * weight != 1.0:
                        weighted_leaves[child.index] = base_weight * weight
            return weighted_leaves

    __magic_key = object()

    @classmethod
    def _create(cls, database: Database, storage_provider: StorageProvider, name: str, description: str = "",
                dimension_type: DimensionType = DimensionType.GENERIC):
        """
        NOT INTENDED FOR EXTERNAL USE! Creates a new dimension.

        :param storage_provider: The storage provider of the database.
        :param name: Name of the dimension to be created.
        :param description: Description of the dimension to be added.
        :return: The new dimension.
        """
        dimension = Dimension(Dimension.__magic_key, database, name, description, dimension_type)
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
    PARENT_WEIGHTS = 11

    MEMBERS = 3
    IDX_MEMBERS = 4

    def __init__(self, dim_creation_key, database:Database, name: str, description: str = "",
                 dimension_type: DimensionType = DimensionType.GENERIC):
        """
        NOT INTENDED FOR DIRECT USE! Cubes and dimensions always need to be managed by a Database.
        Use method 'Database.add_cube(...)' to create objects type Cube.

        :param dim_creation_key:
        :param name:
        :param description:
        """
        assert (dim_creation_key == Dimension.__magic_key), \
            "Objects of type Dimension can only be created through the method 'Database.add_dimension()'."

        self._database = database
        self._name: str = name.strip()
        self._description: str = description
        self._dimension_type = dimension_type

        self.member_defs: dict[int, dict] = {}
        self._member_idx_manager = Dimension.MemberIndexManager()
        self._member_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self._member_idx_list = []
        self.member_counter = 0
        self.highest_idx = 0
        self._members = None
        self._is_weighted: bool = False
        self._weights = Dimension.DimensionWeightManager(self, False)
        self._default_member = None
        # self.get_top_level()

        self._storage_provider: StorageProvider
        self._edit_mode: bool = False
        self._recovery_json = ""
        self._recovery_idx = set()
        self.alias_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()

        self._attributes: Attributes = Attributes(self)
        self._subsets: Subsets = Subsets(self)

    def __str__(self):
        """Returns the string representation of the dimension."""
        return self._name

    def __repr__(self):
        """Returns the string representation of the dimension."""
        return self._name

    def __len__(self):
        """Returns the length (number of member_defs) of the dimension"""
        return len(self.member_defs)

    # region Member accesses by name or index
    def __getitem__(self, item):
        """
        Returns the Member object for a given name or member index.
        :param item: The Member objects name or index.
        :return: The member object.
        """
        return self.member(item)
    # endregion


    @property
    def name(self) -> str:
        """Returns the name of the dimension."""
        return self._name

    @property
    def description(self) -> str:
        """Returns the description of the dimension."""
        return self._description

    @description.setter
    def description(self, value: str):
        """Sets the description of the dimension."""
        self._description = value

    @property
    def dimension_type(self) -> DimensionType:
        """Returns the dimension type of the dimension."""
        return self._dimension_type

    @dimension_type.setter
    def dimension_type(self, value: DimensionType) :
        """Sets the dimension type of the dimension."""
        self._dimension_type = value

    @property
    def attributes(self) -> Attributes:
        """Returns the member attributes defined for the dimension."""
        return self._attributes

    @property
    def edit_mode(self) -> bool:
        """Returns the dimension is in edit mode."""
        return self._edit_mode

    @property
    def subsets(self) -> Subsets:
        """Returns the member attributes defined for the dimension."""
        return self._subsets

    @property
    def is_weighted(self) -> bool:
        """Identifies if the dimension contains any weighted aggregation other
        than +1.0, which is the default for an unweighted plain aggregation."""
        return self._is_weighted

    # region Dimension editing
    def clear(self) -> Dimension:
        """
        Deletes all member_defs and all member_defs from the dimension. Attributes will be kept.

        :return: The dimension itself.
        """
        self._member_idx_lookup = CaseInsensitiveDict()
        self.member_defs = {}
        self._member_idx_manager.clear()
        self.alias_idx_lookup.clear()
        self.member_counter = 0
        self._subsets.clear()
        self._attributes.clear()
        return self

    def edit(self) -> Dimension:
        """
        Sets the dimension into edit mode. Required to add, remove or rename member_defs,
        to add remove or edit subsets or attributes and alike.

        :return: The dimension itself.
        """
        if self._edit_mode:
            raise TinyOlapDimensionEditModeError("Failed to set edit mode. 'edit()' has already been called before.")
        self._edit_mode = True
        self._recovery_json = self.to_json()
        self._recovery_idx = set(self._member_idx_lookup.values())
        return self

    def commit(self) -> Dimension:
        """
        Commits all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        self._update_member_hierarchies()
        if self._storage_provider and self._storage_provider.connected:
            self._storage_provider.add_dimension(self._name, self.to_json())

        # remove data for obsolete member_defs (if any) from database
        obsolete = self._recovery_idx.difference(set(self._member_idx_lookup.values()))
        if obsolete:
            self._database._remove_members(self, obsolete)
        # update member list
        self._member_idx_list = [idx for idx in self.member_defs.keys()]

        # ensure that member level are set correct. This might not be the case when
        # unbalanced hierarchies will be created in random order.
        for idx in self._member_idx_list:
            if self.member_defs[idx][self.LEVEL] == 0:
                self._update_parent_hierarchy_member_levels(idx)

        # update the member list
        self._members = MemberList(self, [
            Member(dimension=self, member_name=self.member_defs[idx][self.NAME],
                   member_level=self.member_defs[idx][self.LEVEL], idx_member=idx,
                   number_format=self.member_defs[idx][self.FORMAT])
            for idx in self.member_defs.keys()
        ])
        # prepare weighting informations.
        self._weights.refresh()
        self._is_weighted = self._weights.is_weighted_dimension

        self._database._flush_cache()
        self._database._update_weighting(self)
        self._edit_mode = False
        return self

    def rollback(self) -> Dimension:
        """
        Rollback all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        self.from_json(self._recovery_json)
        self._edit_mode = False
        return self

    # endregion

    # region member context
    @property
    def members(self) -> MemberList:
        """
        Returns the list of member in the dimension.
        """
        return self._members

    @property
    def root_members(self) -> MemberList:
        """
        Returns a list of root members (members with a parent) of the dimension.
        """
        return MemberList(self, [member for member in self._members if member.is_root])

    @property
    def aggregated_members(self) -> MemberList:
        """
        Returns a list of all aggregated members (members with children) of the dimension.

        """
        return MemberList(self, [member for member in self._members if member.is_parent])

    @property
    def leaf_members(self) -> MemberList:
        """
        Returns a list of all leave members (members without children) of the dimension.
        """
        return MemberList(self, [member for member in self._members if member.is_leaf])

    @property
    def top_level(self) -> int:
        """
        Returns the highest member level available in the dimension. The level of a member
        is equal to the depth of its overall child hierarchy. Leave member have a level of
        0,  their direct parents have 1, their grandparents 2, and so on.
        """
        raise NotImplementedError()

    @property
    def default_member(self) -> Member:
        if not self._default_member:
            self._default_member = self._members[0]
        return self._default_member



    def member(self, member) -> Member:
        if type(member) is int:
            try:
                member_name = self.member_defs[member][1]
                return Member(dimension=self, member_name=member_name,
                              cube=None, idx_dim=-1,
                              idx_member=member,
                              member_level=self.member_defs[self._member_idx_lookup[member_name]][self.LEVEL],
                              number_format=self.member_defs[self._member_idx_lookup[member_name]][self.FORMAT])
            except (IndexError, ValueError):
                raise KeyError(f"Failed to return Member with index '{member}'. The member does not exist.")

        elif member in self._member_idx_lookup:
            idx_member = self._member_idx_lookup[member]
            return Member(dimension=self, member_name=member,
                          cube=None, idx_dim=-1,
                          idx_member=idx_member,
                          member_level=self.member_defs[self._member_idx_lookup[member]][self.LEVEL],
                          number_format=self.member_defs[self._member_idx_lookup[member]][self.FORMAT])
        raise KeyError(f"Failed to return Member '{member}'. The member does not exist.")

    # region add, remove, rename member_defs
    def add_many(self, member, children=None, weights=None, description=None, number_format=None) -> Dimension:
        """Adds one or multiple member_defs and (optionally) associated child-member_defs to the dimension.

        :param member: A single string or an iterable of strings containing the member_defs to be added.
        :param children: A single string or an iterable of strings containing the child member_defs to be added.
               If parameter 'member' is an iterable of strings, then children must be an iterable of same size,
               either containing strings (adds a single child) or itself an iterable of string (adds multiple children).
        :param weights: (optional) the weights to be used to aggregate the children into the parent.
               Default value for aggregation is 1.0. If defined, the shape of the weights arguments (scalar, lists or
               tuples) must have the same shape as the children argument.
        :param description: A description for the member to be added. If parameter 'member' is an iterable,
               then description will be ignored. For that case, please set descriptions for each member individually.
        :param number_format: A format string for output formatting, e.g. for numbers or percentages.
               Formatting follows the standard Python formatting specification at
               <https://docs.python.org/3/library/string.html#format-specification-mini-language>.
        :return Dimension: Returns the dimension itself.
        """
        if not self._edit_mode:
            raise TinyOlapDimensionEditModeError("Failed to add member. Dimension is not in edit mode.")

        member_list = member
        children_list = children
        weight_list = weights
        multi = False

        if isinstance(member, str):
            if not self._valid_member_name(member):
                raise KeyError(f"Failed to add member. Invalid member name '{member}'. "
                               f"'\\t', '\\n' and '\\r' characters are not supported.")

            member_list = [member, ]
            children_list = [children]
            weight_list = [weights]
            multi = True
        elif type(member) is Member:
            member_list = [member.name, ]
            children_list = [children]
            weight_list = [weights]
            multi = True

        if not children:
            children_list = [None] * len(member_list)
            weight_list = [1.0] * len(member_list)


        if weight_list is None:
            weight_list = tuple([tuple(1.0 for member in childs) for childs in children_list])

        # if isinstance(weights, Iterable):
        #     weights_list = weights
        # else:
        #     weights_list = [weights] if weights else [None] * len(member_list)

        for m, c, w in zip(member_list, children_list, weight_list):
            # add the member
            idx_member = self.add(member=m, parent=None,
                                  description=(None if multi else description))
            if number_format:
                self.member_defs[idx_member][self.FORMAT] = number_format

            if c:
                # add the children
                if isinstance(c, str):
                    c = [c]
                    w = [w]

                elif not (isinstance(c, Iterable) and not isinstance(c, str)):
                    raise TinyOlapDimensionEditModeError(
                        f"Failed to member '{m}' to dimension '{self._name}'. Unexpected type "
                        f"'{type(c)}' of parameter 'children' found.")

                if not isinstance(w, Iterable):
                    # copy the structure of c
                    neww = []
                    for cc in c:
                        if not isinstance(cc, str) and not isinstance(cc, Member):
                            ww = []
                            for ccc in cc:
                                if w is None:
                                    ww.append(1.0)
                                else:
                                    ww.append(w)
                        else:
                            if w is None:
                                ww = 1.0
                            else:
                                ww = w
                        neww.append(ww)
                    w = neww

                for child, weight in zip(c, w):
                    if type(child) is Member:
                        child = child.name
                    if not isinstance(child, str):
                        raise TinyOlapDimensionEditModeError(
                            f"Failed to add child to member '{m}' of dimension '{self._name}. Unexpected type "
                            f"'{type(c)}' of parameter 'children' found.")
                    if not self._valid_member_name(child):
                        raise KeyError(f"Failed to add member. Invalid member name '{child}'. "
                                       f"'\\t', '\\n' and '\\r' characters are not supported.")
                    if weight is None:
                        weight = 1.0
                    elif type(weight) is not float:
                        raise TinyOlapDimensionEditModeError(
                            f"Failed to add child to member '{m}' of dimension '{self._name}. Unexpected type "
                            f"'{type(w)}' of parameter 'weight' for child '{child}' found.")

                    self.add(member=child, parent=m, weight=weight)

        return self

    def rename_member(self, member: str, new_name: str, new_description: str = None):
        """Renames a member."""
        if member not in self._member_idx_lookup:
            raise ValueError("Invalid or empty member name.")
        if not new_name:
            raise ValueError("Invalid or empty new member name.")
        if new_name == "*":
            raise ValueError("Invalid member new name. '*' is not a valid member name.")
        if new_name in self.member_defs:
            raise ValueError("New name already exists.")

        idx_member = self._member_idx_lookup[member]
        self.member_defs[idx_member][self.DESC] = (new_description if new_description else member)
        self._member_idx_lookup.pop(member)
        self._member_idx_lookup[new_name] = idx_member

        # adjust subsets
        for subset in self._subsets:
            if member in subset:
                subset._members[new_name] = subset._members.pop(member)
                # idx = subset[self.MEMBERS].index(member)
                # subset[self.MEMBERS][idx] = new_name

    def remove_member(self, member):
        """
        Removes one or multiple member_defs from a dimension.

        :param member: The member or an iterable of member_defs to be deleted.
        """
        member_list = member
        if isinstance(member, str):
            member_list = [member]

        # Ensure all member_defs exist
        for member in member_list:
            if member not in self._member_idx_lookup:
                raise TinyOlapDimensionEditModeError(f"Failed to remove member(s). "
                                                 f"At least 1 of {len(member_list)} member ('{member}') is not "
                                                 f"a member of dimension {self._name}")

        # remove from directly related member_defs
        for member in member_list:
            idx = self._member_idx_lookup[member]
            children = list(self.member_defs[idx][self.CHILDREN])
            parents = list(self.member_defs[idx][self.PARENTS])

            for child in children:
                if idx in self.member_defs[child][self.PARENTS]:
                    self.member_defs[child][self.PARENTS].remove(idx)
            for parent in parents:
                if idx in self.member_defs[parent][self.CHILDREN]:
                    self.member_defs[parent][self.CHILDREN].remove(idx)

        # remove from all related member_defs
        for all_idx in self._member_idx_lookup.values():
            for member_idx in [self._member_idx_lookup[member] in member_list]:
                if member_idx in self.member_defs[all_idx][self.ALL_PARENTS]:
                    self.member_defs[all_idx][self.ALL_PARENTS].remove(member_idx)
                if member_idx in self.member_defs[all_idx][self.BASE_CHILDREN]:
                    self.member_defs[all_idx][self.BASE_CHILDREN].remove(member_idx)

        # remove the member_defs
        member_idx_to_remove = [self._member_idx_lookup[m] for m in member_list]
        self._member_idx_manager.push(member_idx_to_remove)

        for m in member_list:
            del self._member_idx_lookup[m]
        for idx in member_idx_to_remove:
            if idx in self.member_defs:
                del self.member_defs[idx]

        # adjust subsets
        # for subset in self._dict_subsets.values():
        for subset in self._subsets:
            members_to_remove = [member.name for member in subset.members if member in member_list ]
            #members_to_remove = set(member_list).intersection(set( subset.members))
            if members_to_remove:
                for member in members_to_remove:
                    # idx = subset[self.MEMBERS].index(member)
                    # subset[self.MEMBERS].pop(idx)
                    # subset[self.IDX_MEMBERS].pop(idx)
                    subset.members.remove(member)

    # endregion

    # region member aliases
    def member_add_alias(self, member: str, alias: str):
        """
        Adds a member alias to the dimension. Aliases enable the access of member_defs
        by alternative names or address (e.g. a technical key, or an abbreviation).

        :param member: Name of the member to add an alias for.
        :param alias: The alias to be set.
        :raises KeyError: Raised if the member does not exist.
        :raises TinyOlapDuplicateKeyError: Raised if the alias is already used by another member.
                Individual aliases can only be assigned to one member.

        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not member a of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        if alias in self.alias_idx_lookup:
            raise TinyOlapDuplicateKeyError(f"Duplicate alias. The alias '{alias}' is already used "
                                        f"by member '{self.member_defs[idx_member][self.NAME]}' of dimension'{self._name}'")
        self.alias_idx_lookup[alias] = idx_member

    def remove_alias(self, alias: str):
        """
        Removes a member alias from the dimension.

        :param alias: The alias to be removed.
        """
        if alias not in self.alias_idx_lookup:
            raise KeyError(f"{alias}' is not alias a of dimension'{self._name}'")
        del self.alias_idx_lookup[alias]

    def member_remove_all_aliases(self, member: str):
        """
        Removes all aliases of a member from the dimension.

        :param member: Name of the member to remove the aliases for.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not member a of dimension'{self._name}'")
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
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        return idx_member in set(self.alias_idx_lookup.values())

    def member_aliases_count(self, member: str) -> int:
        """
        Returns the number of aliases defined for a given member.

        :param member: Name of the member to be checked.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to return member alias count. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        return len(set([idx for idx in set(self.alias_idx_lookup.values()) if idx == idx_member]))

    def get_member_by_alias(self, alias: str) -> str:
        """
        Returns the name of a member associated with the given.

        :param alias: Name of the alias to be checked.
        :raises KeyError: Raised if the alias does not exist.
        """
        if alias not in self.alias_idx_lookup:
            raise KeyError(f"Failed to get member by alias. '{alias}' is not a member alias of dimension'{self._name}'")
        idx_member = self.alias_idx_lookup[alias]
        return self.member_defs[idx_member][self.NAME]

    def get_member_by_index(self, index: int) -> str:
        """
        Returns the name of a member associated with the given.

        :param index: Index of the member to be returned.
        :raises KeyError: Raised if the alias does not exist.
        """
        if not index in self.member_defs:
            raise KeyError(f"Failed to get member by index. '{index}' is not a member index of dimension'{self._name}'")
        return self.member_defs[index][self.NAME]

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
            raise KeyError(f"Failed to set member number_format. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        self.member_defs[idx_member][self.FORMAT] = format_string

    def member_get_format(self, member: str) -> str:
        """
        Returns the number_format string of a member.

        :param member: Name of the member to return the number_format for.
        :return: Returns the number_format string for the member, or ``None`` if no number_format string is defined.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(
                f"Failed to return member number_format. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        return self.member_defs[idx_member][self.FORMAT]

    def member_remove_format(self, member: str):
        """
        Removes the number_format string of a member.

        :param member: Name of the member to remove the number_format for.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(
                f"Failed to remove member number_format. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        self.member_defs[idx_member][self.FORMAT] = None

    # endregion

    # region member information functions
    def member_get_ordinal(self, member: str) -> int:
        """
        Returns the ordinal position of a member with the list of member_defs of the dimension.

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
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return self._member_idx_lookup[member]

    def member_get_parents(self, member: str) -> MemberList:
        """
        Returns a list of all parents of a member.
        :param member: Name of the member to be evaluated.
        :return: List of parents.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        parents = []
        for idx in self.member_defs[self._member_idx_lookup[member]][self.PARENTS]:
            parents.append(self.member(self.member_defs[idx][self.NAME]))
        return MemberList(self, tuple(parents))

    def member_get_children(self, member: str) -> MemberList:
        """
        Returns a list of all children of a member.

        :param member: Name of the member to be evaluated.
        :return: List of children.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        children = []
        for idx in self.member_defs[self._member_idx_lookup[member]][self.CHILDREN]:
            children.append(self.member(self.member_defs[idx][self.NAME]))
        return MemberList(self, tuple(children))

    def member_get_leaves(self, member) -> MemberList:
        """
        Returns a list of all leave (base level) member_defs of a member.

        :param member: Name of the member to be evaluated.
        :return: List of leave children/member_defs.
        :raises KeyError: Raised if the member does not exist.
        """
        member = str(member)
        if member not in self._member_idx_lookup:
            raise KeyError(f"A member named '{member}' does not exist in dimension'{self._name}'")

        m = self.member_defs[self._member_idx_lookup[member]]
        if m[self.LEVEL] == 0:
            # already a base member, return that
            return MemberList(self, tuple([self.member(member), ]))
        leaves = []
        for idx in m[self.CHILDREN]:
            if self.member_defs[idx][self.LEVEL] > 0:
                members = self.member_get_leaves(self.member_defs[idx][self.NAME])
                leaves.extend(members)
            else:
                leaves.append(self.member(self.member_defs[idx][self.NAME]))
        return MemberList(self, tuple(leaves))

    def member_get_roots(self, member) -> MemberList:
        """
        Returns a list of all root (top level) member_defs of a member.

        :param member: Name of the member to be evaluated.
        :return: List of root parents/member_defs.
        :raises KeyError: Raised if the member does not exist.
        """
        if str(member) not in self._member_idx_lookup:
            raise KeyError(f"A member named '{member}' does not exist in dimension'{self._name}'")

        m = self.member_defs[self._member_idx_lookup[str(member)]]
        if m[self.ALL_PARENTS]:
            return MemberList(self, tuple(
                [self.member(self.member_defs[x][self.NAME]) for x in m[self.ALL_PARENTS]]))
        else:
            # already a root member, return that
            return MemberList(self, tuple([self.member(member), ]))

    def member_get_level(self, member: str):
        """
        Returns the level of a member within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: 0 for leave level member_defs, values > 0 for aggregated member_defs.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return self.member_defs[self._member_idx_lookup[member]][self.LEVEL]

    def member_is_leave(self, member: str):
        """
        Returns True if the member is a leave-level member (member.level = 0) within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: True if the member is a leave-level member, False otherwise.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return self.member_defs[self._member_idx_lookup[member]][self.LEVEL] == 0

    def member_is_root(self, member: str):
        """
        Returns True if the member is a leave-level member (member.level = 0) within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: True if the member is a leave-level member, False otherwise.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return not self.member_defs[self._member_idx_lookup[member]][self.PARENTS]
    # endregion

    # region member enumeration functions (returning lists of member_defs)
    def get_members(self) -> list[str]:
        """
        Returns a list of all member_defs of the dimension.

        :return: List of all member_defs of the dimension.
        """
        return list(self.member_defs[idx][self.NAME] for idx in self._member_idx_lookup.values())
        # return list(str(key) for key in self._member_idx_lookup.keys())

    def get_members_idx(self) -> list[int]:
        """
        Returns a list of indexes of all member_defs of the dimension.

        :return: List of indexes of all member_defs of the dimension.
        """
        return list(self._member_idx_lookup.values())

    def get_members_by_level(self, level: int) -> list[str]:
        """
        Returns a list of all member_defs of the specific member level. 0 identifies the leave level of the dimension.

        :param level: Level of the member_defs to be returned.
        :return: List of member_defs of the specific member level.
        """
        return [self.member_defs[idx_member][self.NAME]
                for idx_member in self.member_defs
                if self.member_defs[idx_member][self.LEVEL] == level]

    def get_top_level(self) -> int:
        """
        Returns the highest member level over all member_defs of the dimension.

        :return: The highest member level over all member_defs of the dimension.
        """
        return max([self.member_defs[idx_member][self.LEVEL] for idx_member in self.member_defs])

    def get_leaves(self) -> list[str]:
        """
        Returns a list of all leave member_defs (member_defs without children = level equals 0) of the dimension.

        :return: List of leave level member_defs of the dimension.
        """
        members = []
        for idx_member in self.member_defs:
            if self.member_defs[idx_member][self.LEVEL] == 0:
                members.append(self.member_defs[idx_member][self.NAME])
        return  members

    def get_aggregated_members(self) -> list[str]:
        """
        Returns a list of all aggregated member_defs (member_defs with children = level greater 0) of the dimension.

        :return: List of aggregated member_defs of the dimension.
        """
        return [self.member_defs[idx_member][self.NAME]
                for idx_member in self.member_defs
                if self.member_defs[idx_member][self.LEVEL] > 0]

    def get_root_members(self) -> list[str]:
        """
        Returns a list of all root member_defs (member_defs with a parent) of the dimension.

        :return: Returns a list of all root member_defs of the dimension.
        """
        members = []
        for idx_member in self.member_defs:
            if not self.member_defs[idx_member][self.PARENTS]:
                members.append(self.member_defs[idx_member][self.NAME])
        return members

    def get_first_member(self) -> str:
        """
        Returns the first member of the dimension.

        :return: Returns the first member_defs of the dimension.
        """
        for idx_member in self.member_defs:
            return self.member_defs[idx_member][self.NAME]
        return ""

    # endregion

    # region attributes
    def attributes_count(self) -> int:
        """
        Returns the number attributes defined in the dimension.

        :return: Number attributes defined in the dimension.
        """
        raise NotImplementedError()
        return len(self._attributes_dict)

    def set_attribute(self, attribute: str, member: str, value):
        """
        Sets an attribute for a specific member of the dimension.

        :param member: Name of the member to set the attribute for.
        :param attribute: Name of the attribute to be set.
        :param value: Value to be set.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :raises TypeError: Raised when the value if not of the expected type.
        """
        raise NotImplementedError()
        if attribute not in self._attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        expected_type = self._attributes[attribute].value_type
        if not type(value) is expected_type:
            raise TypeError(f"Failed to set attribute value. "
                            f"Type of value is '{str(type(value))}' but '{str(expected_type)}' was expected.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self._name}.")
        idx = self._member_idx_lookup[member]
        self.member_defs[idx][self.ATTRIBUTES][attribute] = value

        self._attributes[attribute][member] = value

    def get_attribute(self, attribute: str, member: str):
        """
        Returns the attribute value for a specific member of the dimension.

        :param attribute: Name of the attribute to be returned.
        :param member: Name of the member to get the attribute for.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :return: The value of the attribute, or ``None`` if the attribute is not defined for the specific member.
        """
        raise NotImplementedError()
        warnings.warn("deprecated", DeprecationWarning)

        if attribute not in self._attributes:
            raise KeyError(f"Failed to get attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        if member not in self._attributes[attribute]:
            raise KeyError(f"Failed to get attribute value. "
                           f"'{member}' is not a member of dimension {self._name}.")
        return self._attributes[attribute][member]

        # if member not in self._member_idx_lookup:
        #     raise KeyError(f"Failed to get attribute value. "
        #                    f"'{member}' is not a member of dimension {self._name}.")
        idx = self._member_idx_lookup[member]
        if attribute not in self.member_defs[idx][self.ATTRIBUTES]:
            return None
        return self.member_defs[idx][self.ATTRIBUTES][attribute]


    def get_attribute_type(self, attribute: str):
        """
        Returns the data type of the attribute.

        :param attribute: Name of the attribute to be returned.
        :raises KeyError: Raised when the attribute name does not exist.
        :return: The type of the attribute.
        """
        raise NotImplementedError()
        if attribute not in self._attributes_dict:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        return self._attributes_dict[attribute]

    def has_attribute(self, attribute: str):
        """
        Checks if a specific attribute is defined for the dimension.

        :param attribute: Name of the attribute to be checked.
        :return: ``True``if the attribute exists. ``False`` otherwise.
        """
        return attribute in self._attributes

    def del_attribute_value(self, attribute: str, member: str):
        """
        Deletes an attribute value for a specific member of the dimension.

        :param attribute: Name of the attribute to be deleted.
        :param member: Name of the member to delete the attribute for.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        """
        if attribute not in self._attributes:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self._name}.")

        self._attributes[attribute][member] = None

        # idx = self._member_idx_lookup[member]
        # if attribute in self.member_defs[idx][self.ATTRIBUTES]:
        #     del (self.member_defs[idx][self.ATTRIBUTES][attribute])

    def add_attribute(self, attribute_name: str, value_type: type = object):
        """
        Adds an attribute field to the dimension. Attributes enable to store additional information
        along side of dimension member_defs. Attributes have a value_type which is checked when an attribute
        value is set.

        :param attribute_name: Name of the attribute to be added.
        :param value_type: Type of value expected for the attribute. Default value is ``object`` to allow any data.
        :raises TinyOlapInvalidKeyError: Raised when the name of the attribute is invalid.
        :raises TinyOlapDuplicateKeyError: Raised when the name of the attribute already exists.
        """
        if not is_valid_db_object_name(attribute_name):
            raise TinyOlapInvalidKeyError(f"'{attribute_name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        # if attribute_name in self._attributes_dict:
        if attribute_name in self._attributes:
            raise TinyOlapDuplicateKeyError(f"Failed to add attribute to dimension. "
                                        f"A dimension attribute named '{attribute_name}' already exists.")
        self._attributes[attribute_name] = AttributeField(self, name=attribute_name, value_type=value_type)

    def rename_attribute(self, attribute_name: str, new_attribute_name: str):
        """
        Renames an attribute of a dimension.

        :param attribute_name: The name of the attribute to be renamed.
        :param new_attribute_name: The new name of the attribute.
        :raises TinyOlapInvalidKeyError: Raised when the new name of the attribute is invalid.
        :raises TinyOlapDuplicateKeyError: Raised when the new name of the attribute already exists.
        """
        if not is_valid_db_object_name(new_attribute_name):
            raise TinyOlapInvalidKeyError(f"Failed to rename dimension attribute. "
                                      f"'{new_attribute_name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if attribute_name not in self._attributes_dict:
            raise KeyError(f"Failed to rename dimension attribute. "
                           f"A dimension attribute named '{attribute_name}' does not exist.")

        # add new, remove old attribute values
        for member in self.member_defs.values():
            if attribute_name in member[self.ATTRIBUTES]:
                member[self.ATTRIBUTES][new_attribute_name] = member[self.ATTRIBUTES][attribute_name]
                del (member[self.ATTRIBUTES][attribute_name])

    def remove_attribute(self, attribute_name: str):
        """
        Removes an attribute from the dimension.

        :param attribute_name: Name of the attribute to be removed.
        :raises KeyError: Raises KeyError if the attribute name not exists.

        """
        if attribute_name not in self._attributes:
            raise KeyError(f"Failed to remove attribute from dimension. "
                           f"A dimension attribute named '{attribute_name}' does not exist.")
        # delete all values
        for member in self.member_defs.values():
            if attribute_name in member[self.ATTRIBUTES]:
                del (member[self.ATTRIBUTES][attribute_name])
        self._attributes.remove(attribute_name)

    def get_members_by_attribute(self, attribute_name: str, attribute_value) -> list[str]:
        """
        Returns all member_defs having a specific attribute value.

        :param attribute_name: Name of the attribute to be analyzed.
        :param attribute_value: Value of the attribute to used for filtering.
        :return:
        """

        if attribute_name not in self._attributes:
            raise KeyError(f"Failed to return member_defs by attribute. "
                           f"'{attribute_name}' is not an attribute of dimension {self._name}.")
        members = []

        for idx_member in self.member_defs:
            if attribute_name in self.member_defs[idx_member][self.ATTRIBUTES]:
                if self.member_defs[idx_member][self.ATTRIBUTES][attribute_name] == attribute_value:
                    members.append(self.member_defs[idx_member][self.NAME])

        return members

    # endregion

    # region subsets
    def add_subset(self, subset_name: str, members):
        """
        Adds a new subset to the dimension. A subset is a plain list of member_defs,
        useful for calculation and reporting purposes.

        :param subset_name: Name of the subset to be added.
        :param members: A list (iterable) containing the member to be added to the subset.
        :raises TinyOlapInvalidKeyError: Raised when the name of the subset is invalid.
        :raises TinyOlapDuplicateKeyError: Raised when the name of the subset already exists.
        :raises TypeError: Raised when member_defs list is not of the expected type (list or tuple)
        :raises KeyError: Raised when a member from the member_defs list is not contained in the dimension.
        """
        if not is_valid_db_object_name(subset_name):
            raise TinyOlapInvalidKeyError(f"'{subset_name}' is not a valid dimension subset name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if subset_name in self._subsets:
            raise TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
                                        f"A dimension subset named '{subset_name}' already exists.")

        # validate member_defs list
        if not ((type(members) is list) or (type(members) is tuple)):
            raise TypeError(f"Failed to add member_defs to subset '{subset_name}'. "
                            f"Argument 'member_defs' is not of expected type list or tuple, "
                            f"but of type '{type(subset_name)}'.")
        idx_members = []
        for member in members:
            if member in self._member_idx_lookup:
                idx_members.append(self._member_idx_lookup[member])
            else:
                raise KeyError(f"Failed to add member to subset. "
                               f"'{member}' is not a member of dimension {self._name}.")

        # create and add subset
        self._subsets.add_static_subset(subset_name, members)
        # self._dict_subsets[subset_name] = {self.IDX: self._subset_idx_manager.pop(),
        #                                    self.NAME: subset_name,
        #                                    self.MEMBERS: list(members),
        #                                    self.IDX_MEMBERS: idx_members}

    def has_subset(self, subset_name: str) -> bool:
        """
        Checks if a specific subset is defined for the dimension.

        :param subset_name: Name of the subset to be checked.
        :return: ``True``if the subset exists. ``False`` otherwise.
        """
        return subset_name in self._subsets

    def subsets_count(self) -> int:
        """
        Returns the number subsets defined in the dimension.

        :return: Number subsets defined in the dimension.
        """
        return len(self._subsets)

    def subset_contains(self, subset_name: str, member_name: str) -> bool:
        """
        Checks if a specific member is contained in a subset of the dimension.

        :param subset_name: Name of the subset to be checked.
        :param member_name: Name of the member to be checked.
        :return: ``True``if the member is contained in the subset. ``False`` otherwise.
        """
        if not subset_name in self._subsets:
            raise KeyError(f"Failed to check member contained in subset. "
                           f"'{subset_name}' is not a subset of dimension {self._name}.")
        return member_name in self._subsets[subset_name]

    def rename_subset(self, subset_name: str, new_subset_name: str):
        """
        Renames a subset of the dimension.

        :param subset_name: Name of the subset to be added.
        :param new_subset_name: New name of the subset.
        :raises TinyOlapInvalidKeyError: Raised when the new name for the subset is invalid.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if not is_valid_db_object_name(new_subset_name):
            raise TinyOlapInvalidKeyError(f"'{new_subset_name}' is not a valid dimension subset name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if not subset_name in self._dict_subsets:
            raise KeyError(f"Failed to rename subset. "
                           f"'{subset_name}' is not a subset of dimension {self._name}.")

        subset = self._dict_subsets[subset_name]
        del self._dict_subsets[subset_name]
        self._dict_subsets[new_subset_name] = subset

    def get_subset(self, subset_name: str) -> MemberList:
        """
        Returns the list of member from a subset to the dimension.

        :param subset_name: Name of the subset to be return.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if subset_name in self._subsets:
            return MemberList(self, self._subsets[subset_name])

        raise KeyError(f"Failed to return list of subset member. "
                       f"'{subset_name}' is not a subset of dimension {self._name}.")

    def remove_subset(self, subset_name: str):
        """
        Removes a subset from the dimension.

        :param subset_name: Name of the subset to be removed.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if subset_name in self._subsets:
            self._subsets.remove(subset_name)
            return

        raise KeyError(f"Failed to remove subset. "
                       f"'{subset_name}' is not a subset of dimension {self._name}.")

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
        data = ['{',
                f'"contentType": "{Config.ContentTypes.DIMENSION}", ',
                f'"name": "{self._name}", ',
                f'"description": "{self.description}", ',
                f'"count": {self.member_counter}, ',
                f'"member_defs": {json.dumps(self.member_defs)}, ',
                f'"lookup": {json.dumps(self._member_idx_lookup)}, ',
                f'"subsets": {self._subsets.to_json()}, ',
                f'"attributes": {self._attributes.to_json()}',
                '}',
                ]
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
        :raises TinyOlapFatalError: Raised if an error occurred during the deserialization from json string.
        """
        if not self._edit_mode:
            self.edit()

        try:
            # first, read everything
            dim_def = json.loads(json_string)

            new_name = dim_def["name"]
            new_description = dim_def["description"]
            new_count = dim_def["count"]
            new_members = dim_def["member_defs"]
            new_member_idx_lookup = dim_def["lookup"]
            new_attributes = dim_def["attributes"]
            new_subsets = dim_def["subsets"]

            # json does not allow non-string address, but we use integer address. Conversion is required.
            new_members = dict_keys_to_int(new_members)

            # second, apply everything (this should not fail)
            self._name = new_name
            self.description = new_description
            self.member_counter = new_count
            self.member_defs = new_members
            self._member_idx_lookup = CaseInsensitiveDict().populate(new_member_idx_lookup)
            self._attributes = Attributes(self).from_dict(new_attributes)
            self._subsets = Subsets(self).from_dict(new_subsets)

            self.commit()
        except Exception as err:
            raise TinyOlapFatalError(f"Failed to load json for dimension '{self._name}'. {str(err)}")

    # endregion

    # region auxiliary function to add, remove or rename member_defs
    @staticmethod
    def _valid_member_name(name):
        return not (("\t" in name) or ("\n" in name) or ("\r" in name))

    def add(self, member: str, parent: str, weight: float = 1.0, description: str = None) -> int:
        """
        Adds a member to the dimension. The dimension must be in 'edit' mode.
        :param member: Name of the member to be added.
        :param parent: (optional) Name of a parent-member the member should belong to and aggregate into.
        :param weight: (optional) The weight of the member to be used when aggregating up to the parent-member.
            Default value is +1.0 for normal aggregation. Use -1.0 to subtract the value. Or use any other
            value to define a certain static mathematical dependency between the member and the parent, e.g.,
            .add('Price', 'Price (incl. 5% discount)', 0.95)
            .add('Jan', 'Q1 average', 1.0/3.0)... ,or even better and more explicit
            .add_many('Q1 average', ['Jan', 'Feb', 'Mar'], [1.0/3.0, 1.0/3.0, 1.0/3.0])
        :param description: an optional description for the member.
        :return: An 'int' representing the internal index of the member.
        """
        if member in self._member_idx_lookup:
            member_idx = self._member_idx_lookup[member]
            if description:
                self.member_defs[member_idx][self.DESC] = description
            if parent:
                self._add_parent(member, parent, weight)
        else:
            self.member_counter += 1
            member_idx = self._member_idx_manager.pop()
            self._member_idx_lookup[member] = member_idx
            self.member_defs[member_idx] = {self.IDX: member_idx,
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
                                            self.PARENT_WEIGHTS: {}
                                            }

            if parent:
                self._add_parent(member, parent, weight)
        return member_idx

    def _add_parent(self, member: str, parent: str = None, weight: float = 1.0):
        member_idx = self._member_idx_lookup[member]
        level = self.member_defs[member_idx][self.LEVEL]
        if parent not in self._member_idx_lookup:
            # create parent member
            self.member_counter += 1
            parent_idx = self.member_counter
            self._member_idx_lookup[parent] = parent_idx
            self.member_defs[parent_idx] = {self.IDX: parent_idx,
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
                                            self.PARENT_WEIGHTS: {}
                                            }
            self.member_defs[member_idx][self.PARENT_WEIGHTS][parent_idx] = weight
        else:
            parent_idx = self._member_idx_lookup[parent]
            self.member_defs[parent_idx][self.LEVEL] = level + 1
            if member_idx not in self.member_defs[parent_idx][self.CHILDREN]:
                self.member_defs[parent_idx][self.CHILDREN].append(member_idx)
            self.member_defs[member_idx][self.PARENT_WEIGHTS][parent_idx] = weight

        # add new parent to member
        if parent_idx not in self.member_defs[member_idx][self.PARENTS]:
            self.member_defs[member_idx][self.PARENTS].append(parent_idx)

        # check for circular references
        if self._circular_reference_detection(member_idx, member_idx):
            # remove the relationship
            self.member_defs[member_idx][self.PARENTS].remove(parent_idx)
            self.member_defs[parent_idx][self.CHILDREN].remove(member_idx)

            raise TinyOlapDimensionEditCircularReferenceError(f"Circular reference detected on adding parent <-> child relation "
                                             f"'{self.member_defs[parent_idx][self.NAME]}' <-> "
                                             f"'{self.member_defs[member_idx][self.NAME]}' "
                                             f"to dimension {self._name}. Both members were added to the dimension, "
                                             f"but the parent child relation was not created.")

        # update all-parents list, only relevant for base level member_defs
        self._update_all_parents(member_idx, parent_idx)

    def _update_parent_hierarchy_member_levels(self, idx_member: int, level: int = 0):
        for idx in self.member_defs[idx_member][self.PARENTS]:
            if self.member_defs[idx][self.LEVEL] < level + 1:
                self.member_defs[idx][self.LEVEL] = level + 1
            # update base level children
            self._update_parent_hierarchy_member_levels(idx, level + 1)

    def _update_all_parents(self, idx, parent_idx):
        if self.member_defs[idx][self.LEVEL] > 0:
            for child_idx in self.member_defs[idx][self.CHILDREN]:
                self._update_all_parents(child_idx, parent_idx)
        else:
            if parent_idx not in self.member_defs[idx][self.ALL_PARENTS]:
                self.member_defs[idx][self.ALL_PARENTS].append(parent_idx)

    def _update_member_hierarchies(self):
        for idx in self._member_idx_lookup.values():
            if self.member_defs[idx][self.LEVEL] > 0:
                # update base level children
                self.member_defs[idx][self.BASE_CHILDREN] = self.__get_base_members(idx)
            else:
                self.member_defs[idx][self.ALL_PARENTS] = self.__get_all_parents(idx)

    def _check_circular_reference(self):
        for idx in self._member_idx_lookup.values():
            if self._circular_reference_detection(idx, idx):
                raise TinyOlapDimensionEditModeError(f"Failed to commit dimension. Circular reference detected "
                                                 f"for member {self.member_defs[idx][self.NAME]}.")

    def _circular_reference_detection(self, start: int, current: int, visited=None):
        if visited is None:
            visited = set()

        if current in visited:
            return True

        visited.add(current)
        for parent in self.member_defs[current][self.PARENTS]:
            if self._circular_reference_detection(current, parent, visited):
                return True
        visited.remove(current)
        return False

    def __get_all_parents(self, idx) -> list[int]:
        all_parents = []
        for parent in self.member_defs[idx][self.PARENTS]:
            all_parents.append(parent)
            all_parents = all_parents + self.__get_all_parents(parent)
        return all_parents

    def __get_base_members(self, idx) -> list[int]:
        if self.member_defs[idx][self.LEVEL] == 0:
            return [idx]
        else:
            base_members = []
            for child_idx in self.member_defs[idx][self.CHILDREN]:
                if self.member_defs[child_idx][self.LEVEL] == 0:
                    base_members.append(child_idx)
                else:
                    base_members.append(self.__get_base_members(child_idx))
            return base_members
    # endregion


class DimensionMembers:
    """ Represents the full list of members of a dimension."""

    def __init__(self, dimension, members):
        self._dimension: Dimension = dimension
        super().__init__(members, dimension)

    @property
    def dimension(self):
        return self._dimension

    def add(self, member: str, parent: str, weight: float = 1.0, description: str = None):
        """
        Adds a member to the dimension. The dimension must be in 'edit' mode.
        :param member: Name of the member to be added.
        :param parent: (optional) Name of a parent-member the member should belong to and aggregate into.
        :param weight: (optional) The weight of the member to be used when aggregating up to the parent-member.
            Default value is +1.0 for normal aggregation. Use -1.0 to subtract the value. Or use any other
            value to define a certain static mathematical dependency between the member and the parent, e.g.,
            .add('Price', 'Price (incl. 5% discount)', 0.95)
            .add('Jan', 'Q1 average', 1.0/3.0)... ,or even better and more explicit
            .add_many('Q1 average', ['Jan', 'Feb', 'Mar'], [1.0/3.0, 1.0/3.0, 1.0/3.0])
        :param description: an optional description for the member.
        :return: An 'int' representing the internal index of the member.
        """
        return self._dimension.add(member, parent, weight, description)

    def add_many(self, member, children=None, weights=None, description=None, number_format=None) -> Dimension:
        """Adds one or multiple member_defs and (optionally) associated child-member_defs to the dimension.

        :param member: A single string or an iterable of strings containing the member_defs to be added.
        :param children: A single string or an iterable of strings containing the child member_defs to be added.
               If parameter 'member' is an iterable of strings, then children must be an iterable of same size,
               either containing strings (adds a single child) or itself an iterable of string (adds multiple children).
        :param weights: (optional) the weights to be used to aggregate the children into the parent.
               Default value for aggregation is 1.0. If defined, the shape of the weights arguments (scalar, lists or
               tuples) must have the same shape as the children argument.
        :param description: A description for the member to be added. If parameter 'member' is an iterable,
               then description will be ignored. For that case, please set descriptions for each member individually.
        :param number_format: A format string for output formatting, e.g. for numbers or percentages.
               Formatting follows the standard Python formatting specification at
               <https://docs.python.org/3/library/string.html#format-specification-mini-language>.
        :return Dimension: Returns the dimension itself.
        """
        return self._dimension.add_many(member, children, weights, description, number_format)


    def edit(self) -> Dimension:
        """
        Sets the dimension into edit mode. Required to add, remove or rename member_defs,
        to add remove or edit subsets or attributes and alike.

        :return: The dimension itself.
        """
        return self._dimension.edit()

    def commit(self) -> Dimension:
        """
        Commits all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        return self._dimension.commit()

