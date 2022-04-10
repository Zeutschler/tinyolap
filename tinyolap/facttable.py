# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

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

        def clear(self):
            for i in range(0, self.dims):
                for member_idx, row_list in self._index[i].items():
                    self._index[i][member_idx] = set()

        def get_rows(self, dimension: int, key):
            if key in self._index[dimension]:
                return self._index[dimension][key]
            return set()

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

        def remove_rows(self, deletes, delete_set, shifts):
            shift_set = set(shifts.keys())
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
        def get_size(self) -> int:
            size = 0
            for i in range(0, self.dims):
                for m in self._index[i].values():
                    if m:
                        size += len(m)
            return size

        def get_count(self) -> int:
            count = 0
            for i in range(0, self.dims):
                count += len(self._index[i].keys())
            return count

    def __init__(self, dimensions: int, cube):
        self.row_lookup = {}
        self.facts = []
        self.addresses = []
        self.index = FactTable.FactTableIndex(dimensions)
        self.dims = dimensions
        # we need access to the parent cube. This is a garbage collection safe approach
        self.cube = cube

        self.cached_set = None
        self.cached_idx = []
        self.cached_seq = []
        self.cache_machtes: int = 0
        self.cached_seq_machting = None

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
                self.cube._update_aggregation_index(self.index, address, row)
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

    def clear(self):
        """
        Clears the fact table and resets the index.
        """
        self.row_lookup = {}
        self.facts = []
        self.addresses = []
        self.index.clear()

    def __len__(self):
        return len(self.facts)

    def get_record_by_row(self, row: int):
        return self.addresses[row], self.facts[row]

    def get_value_by_row(self, row, measure):
        if measure in self.facts[row]:
            return self.facts[row][measure]
        return None

    def query(self, idx_address):
        """
        Evaluates the record rows required for an OLAP aggregation.
        :param idx_address: The cell address to be evaluated.
        """
        get_rows = self.index.get_rows
        # get the row sets to be intersected
        sets = []
        for i in range(0, len(idx_address)):
            if idx_address[i] != 0:
                if self.index.exists(i, idx_address[i]):
                    sets.append(get_rows(i, idx_address[i]))
                else:
                    # if the key is not available in the index then no records exist, we're done
                    return set()  # an empty set

        # Order matters most!!! So we order the sets ascending by their length, to intersect smaller sets first.
        # This improves the performance of intersections quite nicely, -10% worst, +200% on average and +600% best.
        seq = sorted(((len(s), d) for d, s in enumerate(sets)))
        # Execute intersection of sets
        result = sets[seq[0][1]]
        for i in range(1, len(seq)):  # do not change to something like <for i,d in seq:>, it's slower.
            result = result.intersection(sets[seq[i][1]])
            if not result:
                # if the set is empty, then there are no records matching the requested address
                break
        return result

    def cached_query(self, idx_address):
        """
        Evaluates the records required for OLAP aggregation using a cache to minimize set operations.
        Using this method only pays back for very special use cases where many aggregations need to be performed
        and subsequent calls have very similar pattern.
        :param idx_address: The cell address to be evaluated.
        """
        get_rows = self.index.get_rows
        sets = []  # an empty set

        # check if we can use the cached base set
        base_set, seq_matching, seq_remaining, caching_requested = self._get_base_set_from_cache(idx_address)

        if base_set:
            sets.append(base_set)
            # get remaining sets to be intersected
            for d, idx in seq_remaining:
                if idx_address[d] != 0:  # 0 = "*", meaning all rows for that dimension, no processing required
                    if self.index.exists(d, idx):
                        sets.append(get_rows(d, idx))

        elif caching_requested:
            # get matching set first and evaluate those
            for d, idx in seq_matching:
                if idx_address[d] != 0:
                    if self.index.exists(d, idx):
                        sets.append(get_rows(d, idx))
                    else:
                        # if the key is not available in the index then no records exist, we're done
                        return set([])  # an empty set

            # Execute intersection of matching sets
            # Order matters most!!! So we order the sets ascending by number of items, to intersect smaller sets first,
            # this improves the performance of intersection quite nicely (±2x up to ±4x times on average).
            seq = sorted(((len(s), d) for d, s in enumerate(sets)))
            base_set = sets[seq[0][1]]
            for len_set, d in seq:
                base_set = base_set.intersection(sets[d])
            sets = [base_set]

            # save to cache
            self.cached_set = base_set
            self.cached_idx = idx_address
            self.cached_seq_machting = seq_matching

            # get remaining sets to be intersected
            for d, idx in seq_remaining:
                if idx_address[d] != 0:  # 0 = "*", meaning all rows for that dimension, no processing required
                    if self.index.exists(d, idx):
                        sets.append(get_rows(d, idx))

        else:
            # get sets to be intersected
            for i in range(0, len(idx_address)):
                if idx_address[i] != 0:
                    if self.index.exists(i, idx_address[i]):
                        sets.append(get_rows(i, idx_address[i]))
                    else:
                        # if the key is not available in the index then no records exist, we're done
                        return set([])  # an empty set
            if not sets:
                # todo: This is not an error! return all rows instead
                raise ValueError(f"Invalid query {idx_address}. At least one dimension needs to be specified.")

        seq = sorted(((len(s), d) for d, s in enumerate(sets)))
        result = sets[seq[0][1]]
        for i in range(1, len(seq)):
            result = result.intersection(sets[seq[i][1]])
            if not result:
                # if the set is empty, then there are no records matching the requested address
                break
        return result

    def _get_base_set_from_cache(self, idx_address) -> (set, list, bool):
        """checks whether a cached base set is available or must be updated."""
        if not self.cached_idx:
            # nothing cached yet
            self.cached_idx = idx_address
            return None, None, None, False

        # compare requested index with cached index
        seq_matching = []
        seq_remaining = []
        matches = 0
        for d in range(self.dims):
            if idx_address[d] == self.cached_idx[d]:
                matches += 1
                seq_matching.append((d, idx_address[d]))
            else:
                seq_remaining.append((d, idx_address[d]))

        # only if there are at least 2 matching indexes, then using the chached set will be beneficial
        if matches > 1:
            if self.cached_seq_machting and self.cached_seq_machting == seq_matching:  # ensure the cache exactly mathes
                return self.cached_set, seq_matching, seq_remaining, False  # 'False' indicates that we keep the cache
            else:
                return None, seq_matching, seq_remaining, True  # the 'True' indicates that caching this cell is requested.
        else:
            # flush the cached set, but remember the index
            self.cached_set = None
            self.cached_seq_machting = None
            self.cached_idx = idx_address
            return None, None, None, False

    def query_area(self, idx_area_def):
        sets = []  # an empty set
        # get first relevant set
        get_rows = self.index.get_rows
        for i in range(0, len(idx_area_def)):
            if idx_area_def[i]:
                for idx_member in idx_area_def[i]:
                    if idx_member != 0:  # "*" means all rows for that dimension, no processing required
                        if self.index.exists(i, idx_member):
                            sets.append(get_rows(i, idx_member))

        if not sets:
            return set()
            # todo: This is not an error! return all rows instead
            raise ValueError(f"Invalid query_area. At least one dimension needs to be specified.")

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

    def remove_records(self, records: set):
        """
        Removes a list of records from the fact table.
        :param records: An iterable of int, identifying the row numbers to be removed.
        :return:
        """
        # 1. find effected records
        delete_set = records
        deletes = []
        delete_addresses = []
        for row, address in enumerate(self.addresses):
            if row in delete_set:
                deletes.append(row)
                delete_addresses.append(address)
        # deletes[] now contains the rows to be deleted in asc sorted order.
        # deletes_addresses[] contains the associated cell addresses

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
        self.index.remove_rows(deletes, delete_set, shifts)