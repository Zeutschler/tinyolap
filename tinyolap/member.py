from __future__ import annotations


class Member:
    """
    Represents a Member from a Dimension. Useful for building business logic
    and navigating though data space.
    """

    def __init__(self, dimension, member_name, cube=None,
                 idx_dim: int = -1, idx_member: int = -1, member_level: int = -1):
        self._idx_dim = idx_dim
        self._idx_member = idx_member
        self._member_level = member_level
        self._dimension = dimension
        self._name = member_name
        self._cube = cube

    def __repr__(self):
        return self._name

    def __str__(self):
        return self._name

    # region Properties
    @property
    def name(self) -> str:
        """Return the name of the member."""
        return self._name

    def full_name(self) -> str:
        """Return the full qualified name of the member, incl. dimension"""
        return self._dimension.name + ":" + self._name

    @property
    def dimension(self):  # -> Dimension:
        """Returns the Dimension object the Member is associated to."""
        return self._dimension

    @property
    def cube(self):  # -> Cube:
        """Return the Cube object the Member is associated to.
        If the Member object is not derived from a Cube or Cursor, ``None``will be returned."""
        return self._cube

    @property
    def has_cube(self) -> bool:
        """Returns ``True`` if the Member object has been derived from a Cube or Cursor context, and
        the Cube property will return an existing Cube instance. If ``False`` is returned, then the
        Cube property will return ``None```"""
        if self._cube:
            return True
        return False

    # endregion

    # region Navigation functions
    def move_first(self) -> Member:
        return NotImplemented

    def move_next(self) -> Member:
        return NotImplemented

    def move_previous(self) -> Member:
        return NotImplemented

    def move_last(self) -> Member:
        return NotImplemented

    def move_up(self) -> Member:
        return NotImplemented

    def move_down(self) -> Member:
        return NotImplemented

    def is_root(self) -> bool:
        return NotImplemented

    def roots_count(self) -> int:
        return NotImplemented

    def move_root(self, index: int = 0) -> Member:
        return NotImplemented

    def is_parent_of(self, member) -> bool:
        return NotImplemented

    def is_parent(self) -> bool:
        return NotImplemented

    def parents_count(self) -> int:
        return NotImplemented

    def move_parent(self, index=0) -> Member:
        return NotImplemented

    def has_parents(self) -> bool:
        return NotImplemented

    def get_children(self):
        return NotImplemented

    def get_base_members(self):
        return NotImplemented

    def is_child_of(self, member) -> bool:
        return NotImplemented

    def is_child(self) -> bool:
        return NotImplemented

    def children_count(self) -> int:
        return NotImplemented

    def move_child(self, index: int = 0) -> Member:
        return NotImplemented

    def has_children(self) -> bool:
        return NotImplemented

    def get_parents(self):
        return NotImplemented

    def level(self) -> int:
        return NotImplemented

    def is_base_member(self) -> bool:
        return NotImplemented

    def is_aggreagrated_member(self) -> bool:
        return NotImplemented

    # endregion
