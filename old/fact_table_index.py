class FactTableIndex:
    """
    Represents a minimalistic multidimensional index over a row store.
    For each member of each dimension a set is maintained containing
    the indexes of all records related to each specific member.
    """
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

    def get_rows(self, dimension: int, key):
        if key in self.index[dimension]:
            return self.index[dimension][key]
        return set([])
