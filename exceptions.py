
class FatalException(Exception):
    """Raised when a fatal error occurs."""
    pass

class KeyNotFoundException(Exception):
    """Raised when a certain member, dimension, table etc. not exist."""
    pass

class InvalidKeyException(Exception):
    """Raised when a certain name of a member, dimension, table etc. is invalid  or not supported."""
    pass


class DuplicateKeyException(Exception):
    """Raised when a certain member, dimension, table etc. was added that already exists."""
    pass


class InvalidMemberNameException(Exception):
    """Raised when a dimension member name is invalid, containing unsupported special characters."""
    pass


class DimensionEditModeException(Exception):
    """Raised when an error occurred while a dimension is in edit mode,
    or if member were added, removed or renamed while not in edit mode.
    Call 'edit_begin()' to start editing."""
    pass

