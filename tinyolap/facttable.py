# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
from copy import deepcopy
import time

class FactTable:
    """
    Stores all records in simple row store and maintains an index
    over all member_defs for faster aggregations and queries.
    """
    __slots__ = 'row_lookup', 'facts', 'addresses', 'index',\
                'dims', 'cube', 'cached_set', 'cached_idx',\
                'cache_matches', 'cached_seq', 'cached_seq_matching',\
                'duration'

    class FactTableRowSet:
        """
        Represents a set of rows matching a certain address pattern, e.g. all rows that
        match the pattern (1, *, 2, *).

        Used to accelerate views. The FactTableRowSet is generated once for the filter dimensions
        of the view and then reused for all cell queries of the view. This can drastically speed
        the performance of views.
        """
        __slots__ = 'pattern', 'idx_pattern', 'idx_residual', 'rows'

        def __init__(self, address: tuple[int], rows:set):
            self.pattern = deepcopy(address)
            self.idx_pattern: tuple = tuple([dim_idx for dim_idx, member in enumerate(address) if member > 0])
            self.idx_residual: tuple = tuple([dim_idx for dim_idx, member in enumerate(address) if member <= 0])
            self.rows = rows

        def match(self, address):
            """
            Checks if an address pattern matches the current rowset pattern,
            e.g., (1, 6, 2, 5) ≈ (1, *, 2, *) := True
            """
            for idx in self.idx_pattern:
                if address[idx] != self.pattern[idx]:
                    return False
            return True

        @property
        def is_empty(self) -> bool:
            """Identifies if the row set is empty."""
            return len(self.rows) == 0

    class FactTableIndex:
        """
        Represents a minimalistic multidimensional index over a row store.
        For each member of each dimension a set is maintained containing
        the indexes of all records related to each specific member.
        """
        __slots__ = 'dims', 'index'

        def __init__(self, dimensions: int):
            self.dims = dimensions
            self.index = []
            for i in range(0, self.dims):
                self.index.append({})

        def set(self, address, row):
            for i in range(0, self.dims):
                if address[i] in self.index[i]:
                    self.index[i][address[i]].add(row)
                else:
                    self.index[i][address[i]] = {row}

        def exists(self, dimension: int, key):
            return key in self.index[dimension]

        def clear(self):
            for i in range(0, self.dims):
                for member_idx, row_list in self.index[i].items():
                    self.index[i][member_idx] = set()

        def get_rows(self, dimension: int, key):
            if key in self.index[dimension]:
                return self.index[dimension][key]
            return set()

        def get_set(self, dimension: int, key):
            if key in self.index[dimension]:
                return self.index[dimension][key]
            return None


        def remove_members(self, dim_idx, members, deletes, delete_set, shifts):
            shift_set = set(shifts.keys())

            # remove the member_defs from the index
            for member in members:
                if member in self.index[dim_idx]:
                    del self.index[dim_idx][member]

            # delete all row references of rows to be deleted
            for i in range(0, self.dims):
                for member_idx, row_list in self.index[i].items():
                    new_row_set = row_list.difference(delete_set)

                    # execute all shifts
                    shifters = new_row_set.intersection(shift_set)
                    if shifters:
                        for shifter in shifters:
                            new_row_set.remove(shifter)
                            new_row_set.add(shifts[shifter])

                    self.index[i][member_idx] = new_row_set

        def remove_rows(self, deletes, delete_set, shifts):
            shift_set = set(shifts.keys())
            # delete all row references of rows to be deleted
            for i in range(0, self.dims):
                for member_idx, row_list in self.index[i].items():
                    new_row_set = row_list.difference(delete_set)

                    # execute all shifts
                    shifters = new_row_set.intersection(shift_set)
                    if shifters:
                        for shifter in shifters:
                            new_row_set.remove(shifter)
                            new_row_set.add(shifts[shifter])

                    self.index[i][member_idx] = new_row_set

        def get_size(self) -> int:
            size = 0
            for i in range(0, self.dims):
                for m in self.index[i].values():
                    if m:
                        size += len(m)
            return size

        def get_count(self) -> int:
            count = 0
            for i in range(0, self.dims):
                count += len(self.index[i].keys())
            return count

    def __init__(self, dimensions: int, cube):
        self.row_lookup = {}
        self.facts = []
        self.addresses = []
        self.index = FactTable.FactTableIndex(dimensions)
        self.dims = dimensions
        # we need access to the parent cube. This is a garbage collection safe approach
        self.cube = cube

        self.duration: float = 0.0

        self.cached_set = None
        self.cached_idx = []
        self.cached_seq = []
        self.cache_matches: int = 0
        self.cached_seq_matching = None


    def set(self, address: tuple, value):
        row = self.row_lookup.get(address, None)

        if row is None:
            # add new record
            row = len(self.facts)
            self.row_lookup[address] = row
            self.facts.append(value)
            self.addresses.append(address)
            # update index
            self.index.set(address, row)
            if self.cube:
                self.cube._update_aggregation_index(self.index, address, row)
            return True

        # overwrite existing record/value
        row = self.row_lookup[address]
        self.facts[row] = value
        return True

    def get(self, address):
        row = self.row_lookup.get(address, None)
        if row is None:
            return None
        return self.facts[row]

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

    def get_value_by_row(self, row):
        return self.facts[row]

    def query(self, address, row_set=None):
        """
        Evaluates the record rows required for an OLAP aggregation.
        :param address: The cell address to be evaluated.
        :param row_set: (optional) a previously evaluated row set.
        """
        contains_all_record_sets = False
        all_record_set = None
        get_set = self.index.get_set
        len_facts = len(self.facts)

        # get the row sets to be intersected
        sets = []
        if row_set:
            # 1. if available, add a pre-populated row set (probably derived from the header dimensions of a view)
            if row_set.is_empty:
                return set()  # no rows available in cube
            residual_dimensions = row_set.idx_residual
            if len(row_set.rows) < len_facts:
                sets.append(row_set.rows)
            else:
                # If a row set contains all records of the cube,
                # then it does not need to be processed at all.
                all_record_set = row_set.rows
                contains_all_record_sets = True
        else:
            residual_dimensions = list(range(0, len(address)))  # we need to process all dimensions

        # 2. process all residual dimensions, not yet contained in the row set
        for i in residual_dimensions:
            if address[i] != 0:
                row_set = get_set(i, address[i])
                if row_set:
                    # Note: If a set contains all records, then it does not
                    #       need to be included in the intersection process.
                    if len(row_set) < len_facts:
                        sets.append(row_set)
                    elif not contains_all_record_sets:
                        # If a row set contains all records of the cube,
                        # then it does not need to be processed at all.
                        all_record_set = row_set
                        contains_all_record_sets = True
                else:
                    return set()  # no rows available in cube

        # 3. check for an edge case: a cell that aggregates all rows of the cube
        if contains_all_record_sets and (not sets):
            return all_record_set

        # The size of sets very much matters for fast intersection!!! Intersect smaller sets first.
        # This improves the performance of intersections quite nicely: -10% worst, +200% on average and +600% best.
        seq = sorted(((len(s), d) for d, s in enumerate(sets)))
        # Execute intersection of sets
        row_set = sets[seq[0][1]]
        for i in range(1, len(seq)):  # do not change to something like <for i,d in seq:>, it's slower.
            row_set = row_set.intersection(sets[seq[i][1]])
            if not row_set:
                # if the set is empty, then there are no records matching the requested address
                break
        return row_set

    def create_row_set(self, address) -> FactTableRowSet:
        """
        Creates a set of rows matching a certain address pattern, e.g. all rows that
        match the pattern (1, *, 2, *). The address needs to contain 0 for all
        '*' members to not be included in the pattern. For more information please
        refer class 'FactTableRowSet'.

        :param address: The cell pattern for the row set.
        """
        return self.FactTableRowSet(address, self.query(address))


    def cached_query(self, idx_address):
        """
        FOR FUTURE USE!
        Evaluates the records required for an OLAP aggregation using a cache to minimize set operations.
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
            self.cached_seq_matching = seq_matching

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
            if self.cached_seq_matching and self.cached_seq_matching == seq_matching:  # ensure the cache exactly mathes
                return self.cached_set, seq_matching, seq_remaining, False  # 'False' indicates that we keep the cache
            else:
                return None, seq_matching, seq_remaining, True  # the 'True' indicates that caching this cell is requested.
        else:
            # flush the cached set, but remember the index
            self.cached_set = None
            self.cached_seq_matching = None
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
        Removes member_defs for a specific dimension from the fact table.
        :param dim_idx: Ordinal index of the dimension affected
        :param members: List of indexes of the member_defs to be removed.
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
