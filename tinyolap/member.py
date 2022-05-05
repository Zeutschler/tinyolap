# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
from tinyolap.utilities.hybrid_dict import HybridDict


class Member:
    """
    Represents a Member of a Dimension. Members are immutable.
    Useful for building business logic and navigation through dimensions and data space.
    """
    _LEVEL = 6
    _NAME = 1
    _FORMAT = 10

    def __init__(self, dimension, member_name, cube=None,
                 idx_dim: int = -1, idx_member: int = -1, member_level: int = -1, number_format: str = ""):
        self._idx_dim = idx_dim
        self._idx_member = idx_member
        self._ordinal = dimension._member_idx_list.index(idx_member)
        self._member_level = member_level
        self._dimension = dimension
        self._name: str = member_name
        self._cube = cube
        self._number_format: str = number_format

        self._children_weights = None
        self._children = None
        self._parents = None
        self._leaves = None
        self._roots = None

    def __repr__(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    # region Attribute access by name
    def __getitem__(self, item):
        """
        Returns the value of a member attribute.
        :param item: Name of the attribute.
        :return: Value of the member attribute.
        """
        return self._dimension.get_attribute(item, self)

    def __setitem__(self, item, value):
        """
        Sets the value of a member attribute.
        :param item: Name of the attribute.
        :param value: Value to be set.
        """
        self._dimension.set_attribute(item, self,  value)

    def __eq__(self, other):
        """Checks if two member instances are equal."""
        if type(other) is Member:
            if self._dimension == other.dimension:
                if self._name == other.name:
                    return True
        else:
            return str(other).lower() == self._name.lower()

    def __hash__(self):
        return hash(self._name)

    # region Properties
    @property
    def name(self) -> str:
        """Returns the name of the member."""
        return self._name

    @property
    def index(self) -> int:
        """ Returns the internal index of the member."""
        return self._idx_member

    @property
    def ordinal(self) -> int:
        """Returns the ordinal position of the member within the overall list of member."""
        return self._ordinal

    @property
    def format(self) -> str:
        """Returns the format string of a member, if defined. Used for number formatting in views.
        If no format is defined, then an empty string will be returned."""
        format_string = self._dimension.member_defs[self._idx_member][self._dimension.FORMAT]
        if format_string:
            return format_string  # self._dimension.member_defs[self._idx_member][self._dimension.FORMAT]
        return ""


    @format.setter
    def format(self, value):
        """
        Sets the format string of a member. Used for number formatting in views.
        :param value: The format string in Python syntax. e.g.: "{:.2%}" for a percentage with 2 digits.
        """
        self._dimension.member_defs[self._idx_member][self._dimension.FORMAT] = value


    @property
    def qualified_name(self) -> str:
        """Returns the full qualified name of the member, incl. dimension"""
        return self._dimension.name + ":" + self._name

    @property
    def dimension(self):  # -> Dimension:
        """Returns the Dimension object the Member is associated to."""
        return self._dimension

    @property
    def cube(self):  # -> Cube:
        """
        Returns the Cube object the Member is associated to.
        If the Member object is not derived from a Cube or Cell, ``None``
        will be returned."""
        return self._cube

    @property
    def has_cube(self) -> bool:
        """Returns ``True`` if the Member object has been derived from a Cube or Cell context, and
        the Cube property will return an existing Cube instance. If ``False`` is returned, then the
        Cube property will return ``None```"""
        if self._cube:
            return True
        return False

    def attribute(self, attribute_name, default_value=None):
        """Returns a specific attribute value for the member."""
        value = self._dimension.get_attribute(attribute_name, self._name)
        if not value:
            value = default_value
        return value


    # endregion

    # region Navigation functions
    def _create_member(self, idx_member):
        """Returns a new Member object."""
        member_level = self._dimension.member_defs[idx_member][self._LEVEL]
        member_name = self._dimension.member_defs[idx_member][self._NAME]
        number_format = self._dimension.member_defs[idx_member][self._FORMAT]
        return Member(self._dimension, member_name, self._cube, self._idx_dim, idx_member,
                      member_level= member_level, number_format=number_format)

    def __update_member(self, idx_member):
        self._idx_member = idx_member
        self.member_level = self._dimension.member_defs[idx_member][self._LEVEL]
        self.member_name = self._dimension.member_defs[idx_member][self._NAME]

    @property
    def first(self) -> Member:
        """
        Returns the first Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            jan = member.first  # 'Jan' is the first month defined in the 'months' dimension.

        :return: A new Member object.
        """
        idx_member = list(self._dimension.member_defs)[0]
        return self._create_member(idx_member)

    @property
    def has_next(self) -> bool:
        """
        Check if a Member has a next Member, meaning it is not already the last member of the dimension.
        """
        return self._ordinal < self._dimension.member_counter - 1

    @property
    def next(self) -> Member:
        """
        Returns the next Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            aug = member.next  # 'Aug' is the next month defined after 'Jul' in the months dimension.

        :return: A new Member object.
        """
        if self._ordinal < self._dimension.member_counter - 1:
            idx_member = self._dimension._member_idx_list[self._ordinal + 1]
            return self._create_member(idx_member)
        return None
        raise IndexError(f"No next member available. Member '{self.member_name}' is already the last member.")

    @property
    def has_previous(self) -> bool:
        """
        Check if a Member has a previous Member, meaning it is not already the first member of the dimension.
        """
        return self._ordinal > 0

    @property
    def previous(self) -> Member:
        """
        Returns the previous Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            jun = member.previous  # 'Jun' is the previous month of 'Jul' in dimension 'months'.

        :return: A new Member object.
        """
        if self._ordinal > 0:
            idx_member = self._dimension._member_idx_list[self._ordinal - 1]
            return self._create_member(idx_member)
        return None
        raise IndexError(f"No previous member available. Member '{self.member_name}' is already the first member.")

    @property
    def last(self) -> Member:
        """
        Returns the last Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            year = member.last  # 'Year Total' is the last member defined in the months dimension.

        :return: A new Member object.
        """
        idx_member = list(self._dimension.member_defs)[-1]
        return self._create_member(idx_member)

    @property
    def has_parents(self) -> bool:
        """
        Check if a Member has at least one parent Member, meaning it is not already a top level member without parents.
        """
        return len(self._dimension.member_defs[self._idx_member][self._dimension.PARENTS]) > 0


    @property
    def first_child(self) -> Member:
        """
        Returns the first child member of a member, if such exists
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()

    @property
    def first_parent(self) -> Member:
        """
        Returns the first parent member of a member, if such exists
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()

    @property
    def first_sibling(self) -> Member:
        """
        Returns the first sibling member (going from left to right) of a member, if such exists.
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()

    @property
    def last_sibling(self) -> Member:
        """
        Returns the last sibling member (going from left to right) of a member, if such exists.
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()

    @property
    def has_siblings(self) -> bool:
        """
        Identifies that the current member has at least one sibling member.
        This method always returns the same value as method 'is_sibling'.
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()

    @property
    def is_sibling(self) -> bool:
        """
        Identifies if the current member is a sibling to at least one other member.
        This method always returns the same value as method 'has_siblings'.
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()

    def sibling(self, offset:int = 1) -> Member:
        """
        Returns a specific sibling member (going from left to right) of a member by an offset, if such exists.
        :param offset: Offset to the sibling member to return. 0 returns the current member itself, +1
        would return the first sibling to the right, -1 the sibling to the left. Higher +/- offsets work
        accordingly.
        :return:
        """
        # todo: Implementation missing
        raise NotImplementedError()


    def parent(self, index: int = 0) -> Member:
        # todo: This may be just a property that returns the very first parent.
        """
        Returns the 1st or subsequent parent of a member. Equal to method ``up`` .

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            q3 = member.parent()  # 'Q3' is the first parent of 'Jul' in the months dimension.

        :param index: Index of the parent to return. 0 returns the first parent, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the Member or if no parent exists.
        :return: A new Member object.
        """
        # return self.up(0)
        return self.up(index)

    def up(self, index: int = 0) -> Member:
        """
        Returns the 1st or subsequent parent of a member. Equal to method ``parent`` .

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            q3 = member.up()  # 'Q3' is the first parent of 'Jul' in the months dimension.

        :type index: Index of the parent to return. 0 returns the first parent, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the Member or if no parent exists.
        :return: A new Member object.
        """
        parents = self._dimension.member_defs[self._idx_member][self._dimension.PARENTS]
        if 0 <= index < len(parents):
            return self._create_member(parents[index])
        raise IndexError(f"Index {index} is out of range of available parents list [0:{len(parents) - 1}] "
                         f"of member {str(self)}.")

    def child(self, index: int = 0) -> Member:
        """
        Returns the 1st or subsequent child of a member. Equal to method ``down`` .

        .. code:: python

            member = cube.dimensions("months").member("Q3")
            jul = member.down()  # 'Jul' is the first child of 'Q3' in the months dimension.
            aug = member.down(1)  # 'Aug' is the second child of 'Q3' in the months dimension.

        :type index: Index of the child to return. 0 returns the first child, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the Member.
        :return: A new Member object.
        """
        return self.down(index)

    def down(self, index: int = 0) -> Member:
        """
        Returns the 1st or subsequent child of a member. Equal to method ``child`` .

        .. code:: python

            member = cube.dimensions("months").member("Q3")
            jul = member.down()  # 'Jul' is the first child of 'Q3' in the months dimension.
            aug = member.down(1)  # 'Aug' is the second child of 'Q3' in the months dimension.

        :type index: Index of the child to return. 0 returns the first child, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the Member.
        :return: A new Member object.
        """
        children = self._dimension.member_defs[self._idx_member][self._dimension.CHILDREN]
        if 0 <= index < len(children):
            return self._create_member(children[index])
        raise IndexError(f"Child index {index} is out of range of available children [0:{len(children) - 1}] "
                         f"of member {str(self)}.")

    @property
    def is_root(self) -> bool:
        """
        Checks if a Member is a root member, meaning the member has no further parents.

        :return: ``True`` is the member is a root member, ``False`` otherwise.
        """
        return len(self._dimension.member_defs[self._idx_member][self._dimension.PARENTS]) == 0

    def root(self, index: int = 0) -> Member:
        """
        Returns the 1st or subsequent root member of a member.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            year = member.root()  # 'Year Total' is the first root level parent of 'Jul' in the months dimension.

        :type index: Index of the root to return. 0 returns the first root, 1 the second ...
        :raises KeyError: Raised, if a root with the given index is not defined for the Member.
        :return: A new Member object.
        """
        roots = self._dimension.get_root_members()
        if 0 <= index < len(roots):
            return self._create_member(roots[index])
        raise IndexError(f"Root index {index} is out of range [0:{len(roots) - 1}] of available root member "
                         f"for dimension {str(self._dimension.name)}.")

    def is_parent_of(self, other_member) -> bool:
        """
        Checks if a Member is a direct parent of another member.

        :return: ``True`` is the other member is a direct parent, ``False`` otherwise.
        """
        return NotImplemented

    @property
    def is_parent(self) -> bool:
        """
        Checks if a Member is a parent of some other member.

        :return: ``True`` is the member is a parent, ``False`` otherwise.
        """
        # return self._dimension.member_defs[self._idx_member][self._dimension.LEVEL] > 0
        return self._member_level > 0

    @property
    def parents_count(self) -> int:
        """
        Returns the number of parents the Member has.

        :return: The number of parents the Member has.
        """
        return len(self._dimension.member_defs[self._idx_member][self._dimension.PARENTS])


    def parent_weight(self, parent:Member) -> float:
        """Returns the weight of the member when rolling up (aggregation) to as specific parent."""
        return self._dimension.member_defs[self._idx_member][self._dimension.PARENT_WEIGHTS].get(parent.index, None)



    @property
    def children(self) -> MemberList:
        """
        Returns a list of all direct children of the member. If the member does not
        have children, then an empty array will be returned.

        :return: List of children.
        """
        if self._children is None:
            idx = self._dimension.member_defs[self._idx_member][self._dimension.CHILDREN]
            if idx:
                members = tuple([self._dimension.member(x) for x in idx])
                self._children = MemberList(self._dimension, members)
            else:
                self._children = tuple()
        return self._children

    @property
    def leaves(self) -> MemberList:
        """
        Returns a list of all leaf (base level) member_defs of the member.
        This method will travers the member hierarchy and collect all
        leaf member_defs. If the member itself is a leaf member, then a
        member list with only the member itself will be returned.

        :return: List of leaf (base level) member_defs.
        """
        if self._leaves is None:
            self._leaves = self._dimension.member_get_leaves(self._name)
        return self._leaves

    @property
    def roots(self) -> MemberList:
        """
        Returns a list of all root (top level) member_defs of the member.
        This method will travers the parent hierarchy and collect all
        root member_defs. If the member itself is a root member, then a
        member list with only the member itself will be returned.

        :return: List of root (base level) member_defs.
        """
        if self._roots is None:
            self._roots = self._dimension.member_get_roots(self._name)
        return self._roots

    def is_child_of(self, other_member) -> bool:
        """
        Checks if a Member is a direct child of another member.

        :return: ``True`` is the other member is a direct child, ``False`` otherwise.
        """
        return NotImplemented

    @property
    def is_child(self) -> bool:
        """
        Checks if a Member is a child of some other (any other) member.

        :return: ``True`` is the member is a child, ``False`` otherwise.
        """
        return len(self._dimension.member_defs[self._idx_member][self._dimension.PARENTS]) > 0

    @property
    def children_count(self) -> int:
        """
        Returns the number of children the Member has.

        :return: The number of children the Member has.
        """
        return len(self._dimension.member_defs[self._idx_member][self._dimension.CHILDREN])

    @property
    def has_children(self) -> bool:
        """
        Checks if a Member has at least one child.

        :return: ``True`` is the member has at least one child, ``False`` otherwise.
        """
        return self._member_level > 0

    @property
    def parents(self) -> MemberList:
        """
        Returns a list of all direct parents of the member. If the member does not
        have parents, then an empty array will be returned.

        :return: List of parents.
        """
        if self._parents is None:
            idx = self._dimension.member_defs[self._idx_member][self._dimension.PARENTS]
            if idx:
                members = tuple([self._dimension.member(x) for x in idx])
                self._parents = MemberList(self._dimension, members)
            else:
                self._parents = tuple()
        return self._parents

    @property
    def level(self) -> int:
        """
        Returns the level of member. 0 indicates base level member_defs, higher values aggregated member_defs.

        :return: Level of the member.
        """
        return self._member_level

    @property
    def is_leaf(self) -> bool:
        """
        Checks if a member is a leaf (base level) member.

        :return: ``True`` is the member is a leaf (base level) member, ``False`` otherwise.
        """
        return self._member_level == 0

    # endregion


class MemberList(HybridDict[Member]):
    """ Represents a list of Member objects."""
    def __init__(self, dimension, members):
        self._dimension = dimension
        super().__init__(members, dimension)

    @property
    def dimension(self):
        return self._dimension

