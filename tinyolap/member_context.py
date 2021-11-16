# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations


class MemberContext:
    """
    Represents a MemberContext of a Dimension. Members are immutable.
    Useful for building business logic and navigation through dimensions and data space.
    """
    _LEVEL = 6
    _NAME = 1

    def __init__(self, dimension, member_name, cube=None,
                 idx_dim: int = -1, idx_member: int = -1, member_level: int = -1):
        self._idx_dim = idx_dim
        self._idx_member = idx_member
        self._ordinal = dimension._member_idx_list.index(idx_member)
        self._member_level = member_level
        self._dimension = dimension
        self._name = member_name
        self._cube = cube

    def __repr__(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    # region Properties
    @property
    def name(self) -> str:
        """Returns the name of the member."""
        return self._name

    @property
    def ordinal(self) -> int:
        """Returns the ordinal position of the member within the overall list of member."""
        return self._ordinal

    @property
    def full_name(self) -> str:
        """Returns the full qualified name of the member, incl. dimension"""
        return self._dimension.name + ":" + self._name

    @property
    def dimension(self):  # -> Dimension:
        """Returns the Dimension object the MemberContext is associated to."""
        return self._dimension

    @property
    def cube(self):  # -> Cube:
        """Returns the Cube object the MemberContext is associated to.
        If the MemberContext object is not derived from a Cube or CellContext, ``None``will be returned."""
        return self._cube

    @property
    def has_cube(self) -> bool:
        """Returns ``True`` if the MemberContext object has been derived from a Cube or CellContext context, and
        the Cube property will return an existing Cube instance. If ``False`` is returned, then the
        Cube property will return ``None```"""
        if self._cube:
            return True
        return False

    # endregion

    # region Navigation functions
    def __get_member(self, idx_member):
        member_level = self._dimension.members[idx_member][self._LEVEL]
        member_name = self._dimension.members[idx_member][self._NAME]
        return MemberContext(self._dimension, member_name, self._cube, self._idx_dim, idx_member, member_level)

    def __update_member(self, idx_member):
        self._idx_member = idx_member
        self.member_level = self._dimension.members[idx_member][self._LEVEL]
        self.member_name = self._dimension.members[idx_member][self._NAME]

    def first(self) -> MemberContext:
        """
        Returns the first MemberContext of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            jan = member.first()  # 'Jan' is the first month defined in the months dimension.

        :return: A new MemberContext object.
        """
        idx_member = list(self._dimension.members)[0]
        return self.__get_member(idx_member)

    def has_next(self) -> bool:
        """
        Check if a MemberContext has a next MemberContext, meaning it is not already the last member of the dimension.
        """
        return self._ordinal < self._dimension.member_counter - 1

    def next(self) -> MemberContext:
        """
        Returns the next MemberContext of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            aug = member.next()  # 'Aug' is the next month defined after 'Jul' in the months dimension.

        :return: A new MemberContext object.
        """
        if self._ordinal < self._dimension.member_counter - 1 :
            idx_member = self._dimension._member_idx_list[self._ordinal + 1]
            return self.__get_member(idx_member)
        raise IndexError(f"Member '{self.member_name}' is already the last member.")

    def has_previous(self) -> bool:
        """
        Check if a MemberContext has a previous MemberContext, meaning it is not already the first member of the dimension.
        """
        return self._ordinal > 0

    def previous(self) -> MemberContext:
        """
        Returns the previous MemberContext of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            jun = member.next()  # 'Jun' is the next month defined before 'Jul' in the months dimension.

        :return: A new MemberContext object.
        """
        if self._ordinal > 0:
            idx_member = self._dimension._member_idx_list[self._ordinal - 1]
            return self.__get_member(idx_member)
        raise IndexError(f"Member '{self.member_name}' is already the first member.")

    def last(self) -> MemberContext:
        """
        Returns the last MemberContext of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            year = member.last()  # 'Year Total' is the last member defined in the months dimension.

        :return: A new MemberContext object.
        """
        idx_member = list(self._dimension.members)[-1]
        return self.__get_member(idx_member)

    def has_parent(self) -> bool:
        """
        Check if a MemberContext has at least one parent MemberContext, meaning it is not already a top level member without parents.
        """
        return len(self._dimension.members[self._idx_member][self._dimension.PARENTS]) > 0

    def parent(self, index: int = 0) -> MemberContext:
        """
        Returns the 1st or subsequent parent of a member. Equal to method ``up`` .

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            q3 = member.up()  # 'Q3' is the first parent of 'Jul' in the months dimension.

        :type index: Index of the parent to return. 0 returns the first parent, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the MemberContext or if no parent exists.
        :return: A new MemberContext object.
        """
        return self.up(index)

    def up(self, index: int = 0) -> MemberContext:
        """
        Returns the 1st or subsequent parent of a member. Equal to method ``parent`` .

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            q3 = member.up()  # 'Q3' is the first parent of 'Jul' in the months dimension.

        :type index: Index of the parent to return. 0 returns the first parent, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the MemberContext or if no parent exists.
        :return: A new MemberContext object.
        """
        parents = self._dimension.members[self._idx_member][self._dimension.PARENTS]
        if 0 <= index < len(parents):
            return self.__get_member(parents[index])
        raise IndexError(f"Parent index {index} is out of range of available parents [0:{len(parents)-1}] "
                         f"of member {str(self)}.")

    def child(self, index: int = 0) -> MemberContext:
        """
        Returns the 1st or subsequent child of a member. Equal to method ``down`` .

        .. code:: python

            member = cube.dimensions("months").member("Q3")
            jul = member.down()  # 'Jul' is the first child of 'Q3' in the months dimension.
            aug = member.down(1)  # 'Aug' is the second child of 'Q3' in the months dimension.

        :type index: Index of the child to return. 0 returns the first child, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the MemberContext.
        :return: A new MemberContext object.
        """
        return self.down(index)

    def down(self, index: int = 0) -> MemberContext:
        """
        Returns the 1st or subsequent child of a member. Equal to method ``child`` .

        .. code:: python

            member = cube.dimensions("months").member("Q3")
            jul = member.down()  # 'Jul' is the first child of 'Q3' in the months dimension.
            aug = member.down(1)  # 'Aug' is the second child of 'Q3' in the months dimension.

        :type index: Index of the child to return. 0 returns the first child, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the MemberContext.
        :return: A new MemberContext object.
        """
        children = self._dimension.members[self._idx_member][self._dimension.CHILDREN]
        if 0 <= index < len(children):
            return self.__get_member(children[index])
        raise IndexError(f"Child index {index} is out of range of available children [0:{len(children)-1}] "
                         f"of member {str(self)}.")

    def is_root(self) -> bool:
        """
        Checks if a MemberContext is a root member, meaning the member has no further parents.

        :return: ``True`` is the member is a root member, ``False`` otherwise.
        """
        return len(self._dimension.members[self._idx_member][self._dimension.PARENTS]) == 0

    def root(self, index: int = 0) -> MemberContext:
        """
        Returns the 1st or subsequent root member of a member.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            year = member.root()  # 'Year Total' is the first root level parent of 'Jul' in the months dimension.

        :type index: Index of the root to return. 0 returns the first root, 1 the second ...
        :raises KeyError: Raised, if a root with the given index is not defined for the MemberContext.
        :return: A new MemberContext object.
        """
        roots = self._dimension.get_root_members()
        if 0 <= index < len(roots):
            return self.__get_member(roots[index])
        raise IndexError(f"Root index {index} is out of range [0:{len(roots)-1}] of available root member "
                         f"for dimension {str(self._dimension.name)}.")

    def is_parent_of(self, other_member) -> bool:
        """
        Checks if a MemberContext is a direct parent of another member.

        :return: ``True`` is the other member is a direct parent, ``False`` otherwise.
        """
        return NotImplemented

    def is_parent(self) -> bool:
        """
        Checks if a MemberContext is a parent of some other member.

        :return: ``True`` is the member is a parent, ``False`` otherwise.
        """
        return self._dimension.members[self._idx_member][self._dimension.LEVEL] > 0

    def parents_count(self) -> int:
        """
        Returns the number of parents the MemberContext has.

        :return: The number of parents the MemberContext has.
        """
        return len(self._dimension.members[self._idx_member][self._dimension.PARENTS])

    def children(self) -> list[MemberContext]:
        """
        Returns a list of all direct children of the member. If the member does not
        have children, then an empty array will be returned.

        :return: List of children.
        """
        return NotImplemented

    def base_members(self) -> list[MemberContext]:
        """
        Returns a list of all base level members of the member. If the member is a base level member itself,
        meaning it does not have children, then an empty array will be returned.

        :return: List of base level members.
        """
        return NotImplemented

    def is_child_of(self, other_member) -> bool:
        """
        Checks if a MemberContext is a direct child of another member.

        :return: ``True`` is the other member is a direct child, ``False`` otherwise.
        """
        return NotImplemented

    def is_child(self) -> bool:
        """
        Checks if a MemberContext is a child of some other member.

        :return: ``True`` is the member is a child, ``False`` otherwise.
        """
        return len(self._dimension.members[self._idx_member][self._dimension.PARENTS]) > 0

    def children_count(self) -> int:
        """
        Returns the number of children the MemberContext has.

        :return: The number of children the MemberContext has.
        """
        return len(self._dimension.members[self._idx_member][self._dimension.CHILDREN])

    def has_children(self) -> bool:
        """
        Checks if a MemberContext has at least one child.

        :return: ``True`` is the member has at least one child, ``False`` otherwise.
        """
        return self._member_level > 0

    def parents(self) -> list[MemberContext]:
        """
        Returns a list of all direct parents of the member. If the member does not
        have parents, then an empty array will be returned.

        :return: List of parents.
        """
        return NotImplemented

    def level(self) -> int:
        """
        Returns the level of member. 0 indicates base level members, higher values aggregated members.

        :return: Level of the member.
        """
        return self._member_level

    def is_base_member(self) -> bool:
        """
        Checks if a MemberContext is a base level member.

        :return: ``True`` is the member is a base level member, ``False`` otherwise.
        """
        return self._member_level == 0

    def is_aggregated_member(self) -> bool:
        """
        Checks if a MemberContext is an aggregated member.

        :return: ``True`` is the member is an aggregated member, ``False`` otherwise.
        """
        return self._member_level > 0

    # endregion
