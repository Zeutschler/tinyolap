import weakref
from old.fact_table_index import FactTableIndex


class FactTable:
    """
    Stores all records in simple row store and maintains an index
    over all members for faster aggregations and queries.
    """
    def __init__(self, dimensions: int, cube=None):
        self.rows = {}
        self.facts = []
        self.tuples = []
        self.index = FactTableIndex(dimensions)
        self.dims = dimensions
        # we need access to the parent cube. This is a garbage collection safe approach
        self.cube = weakref.ref(cube) if cube else None

    def set(self, address, measure, value):
        record_hash = hash(address)
        if record_hash in self.rows:
            # overwrite existing record/value
            row = self.rows[record_hash]
            self.facts[row][measure] = value
            return True
        else:
            # add new record
            row = len(self.facts)
            self.rows[record_hash] = row
            self.facts.append({measure: value})
            self.tuples.append(address)
            # update index
            self.index.set(address, row)
            if self.cube:
                cube = self.cube()
                cube._update_aggregation_index(self.index, address, row)
            return True

    def get(self, address, measure):
        record_hash = hash(address)
        if record_hash in self.rows:
            # overwrite existing record/value
            row = self.rows[record_hash]
            if measure in self.facts[row]:
                return self.facts[row][measure]
        return 0.0

    def get_facts(self, record):
        record_hash = hash(record)
        if record_hash in self.rows:
            # overwrite existing record/value
            row = self.rows[record_hash]
            return self.facts[row]
        return None

    def __len__(self):
        return len(self.facts)

    def get_record_by_row(self, row: int):
        return self.tuples[row], self.facts[row]

    def get_value_by_row(self, row, measure):
        if measure in self.facts[row]:
            return self.facts[row][measure]
        return None

    def query(self, query):
        first = 1
        result = set([])  # an empty set
        # get first relevant index
        for i in range(0, len(query)):
            if query[i] != 0:  # "*" means all rows for that dimension, no processing required
                if self.index.exists(i, query[i]):
                    result = self.index.get_rows(i, query[i])
                    first = i + 1
                    break
        if not result:
            raise ValueError(f"Invalid query {query}. At least one dimension needs to be specified.")

        # intersect with all other (relevant) dimensions
        for i in range(first, len(query)):
            if query[i] != 0:  # "*" means all rows for that dimension, no processing required
                if self.index.exists(i, query[i]):
                    result = result.intersection(self.index.get_rows(i, query[i]))
                else:
                    # if the key is not available in the index then no records exist
                    return set([])  # an empty set
        return result
