from __future__ import annotations


class Member:
    """
    Represents a Member of a Dimension. Members are immutable.
    Useful for building business logic and navigation through dimensions and data space.
    """
    _LEVEL = 6
    _NAME = 1

    def __init__(self, dimension, member_name, cube=None,
                 idx_dim: int = -1, idx_member: int = -1, member_level: int = -1):
        self._idx_dim = idx_dim
        self._idx_member = idx_member
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
    def full_name(self) -> str:
        """Returns the full qualified name of the member, incl. dimension"""
        return self._dimension.name + ":" + self._name

    @property
    def dimension(self):  # -> Dimension:
        """Returns the Dimension object the Member is associated to."""
        return self._dimension

    @property
    def cube(self):  # -> Cube:
        """Returns the Cube object the Member is associated to.
        If the Member object is not derived from a Cube or Cell, ``None``will be returned."""
        return self._cube

    @property
    def has_cube(self) -> bool:
        """Returns ``True`` if the Member object has been derived from a Cube or Cell context, and
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
        return Member(self._dimension, member_name,self._cube, self._idx_dim, idx_member, member_level)

    def __update_member(self, idx_member):
        self._idx_member = idx_member
        self.member_level = self._dimension.members[idx_member][self._LEVEL]
        self.member_name = self._dimension.members[idx_member][self._NAME]

    def first(self) -> Member:
        """
        Returns the first Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            jan = member.first()  # 'Jan' is the first month defined in the months dimension.

        :return: A new Member object.
        """
        idx_member = list(self._dimension.members)[0]
        self.__update_member(idx_member)
        return True

    def next(self) -> Member:
        """
        Returns the next Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            aug = member.next()  # 'Aug' is the next month defined after 'Jul' in the months dimension.

        :return: A new Member object.
        """
        return NotImplemented

    def previous(self) -> Member:
        """
        Returns the previous Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            jun = member.next()  # 'Jun' is the next month defined before 'Jul' in the months dimension.

        :return: A new Member object.
        """
        return NotImplemented

    def last(self) -> Member:
        """
        Returns the last Member of the dimension by its ordinal position.

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            year = member.last()  # 'Year Total' is the last period defined in the months dimension.

        :return: A new Member object.
        """
        return NotImplemented

    def parent(self, index: int = 0) -> Member:
        """
        Returns the 1st or subsequent parent of a member. Equal to method ``up`` .

        .. code:: python

            member = cube.dimensions("months").member("Jul")
            q3 = member.up()  # 'Q3' is the first parent of 'Jul' in the months dimension.

        :type index: Index of the parent to return. 0 returns the first parent, 1 the second ...
        :raises KeyError: Raised, if a parent with the given index is not defined for the Member or if no parent exists.
        :return: A new Member object.
        """
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
        return NotImplemented

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
        return NotImplemented

    def is_root(self) -> bool:
        """
        Checks if a Member is a root member, meaning the member has no further parents.

        :return: ``True`` is the member is a root member, ``False`` otherwise.
        """
        return NotImplemented

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
        return NotImplemented

    def is_parent_of(self, other_member) -> bool:
        """
        Checks if a Member is a direct parent of another member.

        :return: ``True`` is the other member is a direct parent, ``False`` otherwise.
        """
        return NotImplemented

    def is_parent(self) -> bool:
        """
        Checks if a Member is a parent of some other member.

        :return: ``True`` is the member is a parent, ``False`` otherwise.
        """
        return NotImplemented

    def parents_count(self) -> int:
        """
        Returns the number of parents the Member has.

        :return: The number of parents the Member has.
        """
        return NotImplemented

    def has_parents(self) -> bool:
        """
        Checks if a Member has at least one parent.

        :return: ``True`` is the member has at least one parent, ``False`` otherwise.
        """
        return NotImplemented

    def children(self) -> list[Member]:
        """
        Returns a list of all direct children of the member. If the member does not
        have children, then an empty array will be returned.

        :return: List of children.
        """
        return NotImplemented

    def base_members(self):
        """
        Returns a list of all base level members of the member. If the member is a base level member itself,
        meaning it does not have children, then an empty array will be returned.

        :return: List of base level mebers.
        """
        return NotImplemented

    def is_child_of(self, other_member) -> bool:
        """
        Checks if a Member is a direct child of another member.

        :return: ``True`` is the other member is a direct child, ``False`` otherwise.
        """
        return NotImplemented

    def is_child(self) -> bool:
        """
        Checks if a Member is a child of some other member.

        :return: ``True`` is the member is a child, ``False`` otherwise.
        """
        return NotImplemented

    def children_count(self) -> int:
        """
        Returns the number of children the Member has.

        :return: The number of children the Member has.
        """
        return NotImplemented

    def has_children(self) -> bool:
        """
        Checks if a Member has at least one child.

        :return: ``True`` is the member has at least one child, ``False`` otherwise.
        """
        return NotImplemented

    def parents(self) -> list[Member]:
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
        return NotImplemented

    def is_base_member(self) -> bool:
        """
        Checks if a Member is a base level member.

        :return: ``True`` is the member is a base level member, ``False`` otherwise.
        """
        return NotImplemented

    def is_aggreagrated_member(self) -> bool:
        """
        Checks if a Member is an aggregated member.

        :return: ``True`` is the member is an aggregated member, ``False`` otherwise.
        """
        return NotImplemented

    # endregion
