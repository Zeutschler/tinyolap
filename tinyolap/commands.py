"""Provides various commands for undo/redo actions within TinyOlap."""
import datetime
from abc import ABC, abstractmethod
import time
from collections import Iterable


class Command(ABC):
    """Command base class for TinyOlap commands."""
    def __init__(self):
        super().__init__()
        self.timestamp = datetime.datetime.now()
        self.undone: bool = False

    @abstractmethod
    def undo(self, database) -> bool:
        """Undo the command."""
    @abstractmethod
    def redo(self, database) -> bool:
        """Redo the command."""


class CompoundCommand():
    """Command that represents a list of related commands,
     e.g. a multi-value transaction."""
    def __init__(self, commands):
        super().__init__()
        self.undone = False
        if isinstance(commands, Iterable):
            self.commands = commands
        else:
            self.commands = [commands,]

    def undo(self, database) -> bool:
        """Undo the command."""
        result = True
        for command in self.commands:
            result &= command.undo(database)
        self.undone = True
        return result

    def redo(self, database) -> bool:
        """Redo the command."""
        result = True
        for command in self.commands:
            result &= command.redo(database)
        self.undone = False
        return result


class CubeSetCommand(Command):
    """Command to set a cube value."""
    def __init__(self, cube: str, idx_address: tuple[int], before, after):
        super().__init__()
        self.undone = False
        self.cube = cube
        self.idx_address = idx_address
        self.before = before
        self.after = after

    def undo(self, database) -> bool:
        """Undo the command."""
        database.cubes[self.cube]._set_base_level_cell(self.idx_address, 0, self.before)
        self.undone = True
        return True

    def redo(self, database) -> bool:
        """Redo the command."""
        database.cubes[self.cube]._set_base_level_cell(self.idx_address, 0, self.after)
        self.undone = False
        return True


class AttributeSetCommand(Command):
    """Command to set a dimension attribute."""
    def __init__(self, dimension: str, attribute, member: str, before, after):
        super().__init__()
        self.undone = False
        self.dimension = dimension
        self.attribute = attribute
        self.member = member
        self.before = before
        self.after = after

    def undo(self, database) -> bool:
        """Undo the command."""
        database.dimensions[self.dimension].set_attribute(self.attribute, self.member, self.before)
        self.undone = True
        return True

    def redo(self, database) -> bool:
        """Redo the command."""
        database.dimensions[self.dimension].set_attribute(self.attribute, self.member, self.after)
        self.undone = False
        return True

