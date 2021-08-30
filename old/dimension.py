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

    def __init__(self, name: str):
        self.name = name.strip()
        self.member_idx_lookup = {}
        self.members = {}
        self.member_counter = 0

    def __str__(self):
        return f"dimension '{self.name}'"

    def __repr__(self):
        return f"dimension '{self.name}'"

    def clear(self):
        """Deletes all members from the dimension."""
        self.member_idx_lookup = {}
        self.members = {}
        self.member_counter = 0

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

    def member_add(self, member: str, parent: str = None, description: str = None):
        """Adds a member and (optionally) a parent-member to the dimension."""
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
                                        }

            if parent:
                self.__add_parent(member, parent)

    def __add_parent(self, member: str, parent: str = None):
        member_idx = self.member_idx_lookup[member]
        if parent not in self.member_idx_lookup:
            level = self.members[member_idx][self.LEVEL]
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
                                        self.LEVEL: level + 1}
        else:
            parent_idx = self.member_idx_lookup[parent]
            if member_idx not in self.members[parent_idx][self.CHILDREN]:
                self.members[parent_idx][self.CHILDREN].append(member_idx)

        # add new parent to member
        if parent_idx not in self.members[member_idx][self.PARENTS]:
            self.members[member_idx][self.PARENTS].append(parent_idx)

        # update all parents list, only relevant for base level members
        self.__update_all_parents(member_idx, parent_idx)

    def __update_all_parents(self, idx, parent_idx):
        if self.members[idx][self.LEVEL] > 0:
            for child_idx in self.members[idx][self.CHILDREN]:
                self.__update_all_parents(child_idx, parent_idx)
        else:
            if parent_idx not in self.members[idx][self.ALL_PARENTS]:
                self.members[idx][self.ALL_PARENTS].append(parent_idx)

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

    def member_delete(self, member: str):
        """Deletes a member. NOT YET IMPLEMENTED!"""
        raise NotImplemented(f"Deletion of members is not (yet) supported.'")

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
