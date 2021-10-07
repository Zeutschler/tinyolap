class TinyOlapException(Exception):
    """Base class for all tinyOlap specific exceptions."""
    pass


class CubeFormulaException(TinyOlapException):
    """Raised when an rule in a cube fails."""
    pass


class InvalidCellAddressException(TinyOlapException):
    """Raised when an invalid cube cell address is detected."""
    pass


class InvalidOperationException(TinyOlapException):
    """Raised when the invalid operation on a database object is executed."""
    pass


class CubeCreationException(TinyOlapException):
    """Raised when the creation of a cube."""
    pass


class DimensionInUseException(TinyOlapException):
    """Raised when the deletion of a dimension failed to to being used by a cube."""
    pass


class DatabaseFileException(TinyOlapException):
    """Raised when an error occurs while handling database files."""
    pass


class FatalException(TinyOlapException):
    """Raised when a fatal error occurs."""
    pass


class KeyNotFoundException(TinyOlapException):
    """Raised when a certain member, dimension, table etc. not exist."""
    pass


class InvalidKeyException(TinyOlapException):
    """Raised when a certain name of a member, dimension, table etc. is invalid  or not supported."""
    pass


class DuplicateKeyException(TinyOlapException):
    """Raised when a certain member, dimension, table etc. was added that already exists."""
    pass


class InvalidMemberNameException(TinyOlapException):
    """Raised when a dimension member name is invalid, containing unsupported special characters."""
    pass


class DimensionEditModeException(TinyOlapException):
    """Raised when an error occurred while a dimension is in edit mode,
    or if member were added, removed or renamed while not in edit mode.
    Call 'edit_begin()' to start editing."""
    pass
