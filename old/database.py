import os
import sqlite3
from typing import List, Set, Tuple, Dict

from database_serializer import DatabaseSerializer
from cube import Cube
from dimension import Dimension


class Database:
    def __init__(self, server=None, name: str = None):
        self.dimensions: Dict[Dimension] = {}
        self.cubes: Dict[Cube] = {}
        self.database_file = None
        if not name:
            self.name: str = "db"
        else:
            self.name: str = name
        self.server = server
        self.serializer: DatabaseSerializer = DatabaseSerializer(self)

    def add_dimension(self, dimension: Dimension):
        pass



    def set(self, cube: str, address: Tuple[str], measure: str, value: float):
        """Writes a value to the database for the given cube, address and measure."""
        return False

    def get(self, cube: str, address: Tuple[str], measure: str):
        """Returns a value from the database for a given cube, address and measure.
                If no records exist for the given address, then 0.0 will be returned."""
        return False
