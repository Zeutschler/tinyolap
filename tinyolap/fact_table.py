import weakref


class FactTable:
    """
    Stores all records in simple row store and maintains an index
    over all members for faster aggregations and queries.
    """

    class FactTableIndex:
        """
        Represents a minimalistic multidimensional index over a row store.
        For each member of each dimension a set is maintained containing
        the indexes of all records related to each specific member.
        """

        def __init__(self, dimensions: int):
            self.dims = dimensions
            self._index = []
            for i in range(0, self.dims):
                self._index.append({})

        def set(self, address, row):
            for i in range(0, self.dims):
                if address[i] in self._index[i]:
                    self._index[i][address[i]].add(row)
                else:
                    self._index[i][address[i]] = {row}

        def exists(self, dimension: int, key):
            return key in self._index[dimension]

        def get_rows(self, dimension: int, key):
            if key in self._index[dimension]:
                return self._index[dimension][key]
            return set([])

        def remove_members(self, dim_idx, members, deletes, delete_set, shifts):
            shift_set = set(shifts.keys())

            # remove the members from the index
            for member in members:
                if member in self._index[dim_idx]:
                    del self._index[dim_idx][member]

            # delete all row references of rows to be deleted
            for i in range(0, self.dims):
                for member_idx, row_list in self._index[i].items():
                    new_row_set = row_list.difference(delete_set)

                    # execute all shifts
                    shifters = new_row_set.intersection(shift_set)
                    if shifters:
                        for shifter in shifters:
                            new_row_set.remove(shifter)
                            new_row_set.add(shifts[shifter])

                    self._index[i][member_idx] = new_row_set


    def __init__(self, dimensions: int, cube=None):
        self.row_lookup = {}
        self.facts = []
        self.addresses = []
        self.index = FactTable.FactTableIndex(dimensions)
        self.dims = dimensions
        # we need access to the parent cube. This is a garbage collection safe approach
        self.cube = weakref.ref(cube) if cube else None

    def set(self, address: tuple, measure, value):
        record_hash = hash(address)
        if record_hash in self.row_lookup:
            # overwrite existing record/value
            row = self.row_lookup[record_hash]
            self.facts[row][measure] = value
            return True
        else:
            # add new record
            row = len(self.facts)
            self.row_lookup[record_hash] = row
            self.facts.append({measure: value})
            self.addresses.append(address)
            # update index
            self.index.set(address, row)
            if self.cube:
                cube = self.cube()
                cube._update_aggregation_index(self.index, address, row)
            return True

    def get(self, address, measure):
        record_hash = hash(address)
        if record_hash in self.row_lookup:
            # overwrite existing record/value
            row = self.row_lookup[record_hash]
            if measure in self.facts[row]:
                return self.facts[row][measure]
        return 0.0

    def get_facts(self, record):
        record_hash = hash(record)
        if record_hash in self.row_lookup:
            # overwrite existing record/value
            row = self.row_lookup[record_hash]
            return self.facts[row]
        return None

    def __len__(self):
        return len(self.facts)

    def get_record_by_row(self, row: int):
        return self.addresses[row], self.facts[row]

    def get_value_by_row(self, row, measure):
        if measure in self.facts[row]:
            return self.facts[row][measure]
        return None

    def query(self, query):
        first = 1
        sets = []  # an empty set
        result = set([])
        # get first relevant set
        get_rows = self.index.get_rows
        for i in range(0, len(query)):
            if query[i] != 0:  # "*" means all rows for that dimension, no processing required
                if self.index.exists(i, query[i]):
                    sets.append(get_rows(i, query[i]))
                    first = i + 1
                else:
                    # if the key is not available in the index then no records exist
                    return set([])  # an empty set
        if not sets:
            # todo: This is not an error! return all rows instead
            raise ValueError(f"Invalid query {query}. At least one dimension needs to be specified.")

        # Execute intersection of sets
        # Order matters most!!! order the sets by ascending number of items, this greatly
        # improves the performance of intersection operations.
        seq = sorted(((len(s), i) for i, s in enumerate(sets)))
        result = sets[seq[0][1]]
        for i in range(1, len(seq)):
            result = result.intersection(sets[seq[i][1]])
        return result

    def remove_members(self, dim_idx: int, members: ()):
        """
        Removes members for a specific dimension from the fact table.
        :param dim_idx: Ordinal index of the dimension affected
        :param members: List of indexes of the members to be removed.
        :return:
        """
        # 1. find effected records
        deletes = []
        for row, address in enumerate(self.addresses):
            if address[dim_idx] in members:
                deletes.append(row)
        delete_set = set(deletes)
        # deletes[] now contains the rows to be deleted in asc sorted order.

        # 2. prepare shifting of row positions for all records
        #    create tuples with (old_position, new position)
        shifts = {}
        shift = 0
        row = -1
        for del_row in deletes:
            if row == -1:
                shift += 1
                row = del_row + 1
            else:
                for r in range(row, del_row):  # from the start...
                    shifts[r] = r - shift
                shift += 1
                row = del_row + 1
        for r in range(row, len(self.row_lookup)):  # ...up to the end
            shifts[r] = r - shift

        # 3.1 update the lookup table indexes...
        temp_lookup = self.row_lookup.copy()
        # 3.2 ...then delete the obsolete records
        self.row_lookup = {address: row for address, row in self.row_lookup.items() if row not in delete_set}
        for k, v in temp_lookup.items():
            if v in shifts:
                self.row_lookup[k] = shifts[v]

        # 4. remove records
        self.facts = [data for row, data in enumerate(self.facts) if row not in delete_set]
        self.addresses = [data for row, data in enumerate(self.addresses) if row not in delete_set]

        # 5. finally update the index
        self.index.remove_members(dim_idx, members, deletes, delete_set, shifts)
