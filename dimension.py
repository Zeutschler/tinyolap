import json
from collections.abc import Iterable
import collections.abc
from exceptions import *
import util


class Dimension:
    """
    Represents a Dimension containing a set of members and their parent-child relations.
    Dimension are used to define multi-dimensional space and aggregations for Cubes.
    """
    IDX = 0
    NAME = 1
    DESC = 2
    PARENTS = 3
    CHILDREN = 4
    ALL_PARENTS = 5
    LEVEL = 6
    ATTRIBUTES = 7
    BASE_CHILDREN = 8

    def __init__(self, name: str, description: str = ""):
        self.name: str = name.strip()
        self.description: str = description
        self.members: dict[int, dict] = {}
        self.member_idx_lookup: dict[str, int] = {}
        self.attributes = {}
        self.subsets = {}
        self.member_counter = 0
        self.highest_idx = 0
        self.backend = None
        self.edit_mode: bool = False
        self.recovery_json = ""
        self.recovery_idx = set()
        self.database = None

    def __str__(self):
        return f"dimension '{self.name}'"

    def __repr__(self):
        return f"dimension '{self.name}'"

    def clear(self):
        """Deletes all members from the dimension."""
        self.member_idx_lookup = {}
        self.members = {}
        self.member_counter = 0

    def edit_begin(self):
        """Sets the dimension into edit mode. Required to add, remove or rename members,
        to add remove or edit subsets or attributes and alike."""
        if self.edit_mode:
            raise DimensionEditModeException("Failed to set edit mode. 'edit_begin()' was already called before.")
        self.edit_mode = True
        self.recovery_json = self.to_json()
        self.recovery_idx = set(self.member_idx_lookup.values())

    def edit_commit(self):
        """Commits all changes since 'edit_begin()' was called and ends the edit mode."""
        self.__update_member_hierachies()
        if self.backend:
            self.backend.dimension_update(self, self.to_json())
        # remove data for obsolete members (if any) from database
        obsolete = self.recovery_idx.difference(set(self.member_idx_lookup.values()))
        if obsolete:
            self.database.__remove_members(self, obsolete)
        self.edit_mode = False

    def edit_rollback(self):
        """Rollback all changes since 'edit_begin()' was called and ends the edit mode."""
        self.from_json(self.recovery_json)
        self.edit_mode = False

    def __len__(self):
        return len(self.members)

    def get_members(self):
        """Returns all members of the dimension."""
        return self.member_idx_lookup.keys()

    def get_members_by_level(self, level: int):
        """Returns all members of a specific level."""
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] == level]

    def get_top_level(self):
        """Returns the highest member level over all members of the dimension."""
        return max([self.members[idx_member][self.LEVEL] for idx_member in self.members])

    def get_leave_members(self):
        """Returns all leave members (members without children) of the dimension."""
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] == 0]

    def get_aggregated_members(self):
        """Returns all aggregated members (members with children) of the dimension."""
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if self.members[idx_member][self.LEVEL] > 0]

    def get_root_members(self):
        """Returns all root members (members with a parent) of the dimension."""
        return [self.members[idx_member][self.NAME]
                for idx_member in self.members
                if not self.members[idx_member][self.PARENTS]]

    def member_add(self, member, children=None, description=None):
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
                    self.__member_add_parent_child(member=child, parent=m, weight=1.0)

    def __member_add_parent_child(self, member, parent, weight: float = 1.0, description: str = None):
        if member in self.member_idx_lookup:
            member_idx = self.member_idx_lookup[member]
            if description:
                self.members[member_idx][self.DESC] = description
            if parent:
                self.__add_parent(member, parent)
        else:
            self.member_counter += 1
            member_idx = self.member_counter
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
                base_children = []
                # update base level children
                self.members[idx][self.BASE_CHILDREN] = self.__get_base_members(idx)

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

    def member_rename(self, member: str, new_name: str, new_description: str = None):
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

    def member_remove(self, member):
        """Removes on or multiple members from a dimension."""
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
        member_idx = [self.member_idx_lookup[m] for m in member_list]
        for m in member_list:
            del self.member_idx_lookup[m]
        for idx in member_idx:
            if idx in self.members:
                del self.members[idx]

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
        return self.members[self.member_idx_lookup[member]][self.CHILDREN]

    def member_get_level(self, member: str):
        """Returns the level of a member within the member hierarchy.
        Value 0 identifies leave members, values greater 0 identify aggregated members."""
        if member not in self.member_idx_lookup:
            raise ValueError(f"A member named '{member}' is not defined in dimension'{self.name}'")
        return self.members[self.member_idx_lookup[member]][self.LEVEL]

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
            self.edit_begin()

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
            new_members = util.dict_keys_to_int(new_members)

            # second, apply everything (this should not fail)
            self.name = new_name
            self.description = new_description
            self.member_counter = new_count
            self.members = new_members
            self.member_idx_lookup = new_member_idx_lookup
            self.attributes = new_attributes
            self.subsets = new_subsets
            self.edit_commit()
        except Exception as err:
            raise FatalException(f"Failed to load json for dimension '{self.name}'. {str(err)}")
