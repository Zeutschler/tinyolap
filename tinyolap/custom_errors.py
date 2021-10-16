# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

class TinyOlapError(Exception):
    """Base class for all tinyOlap specific exceptions."""
    pass


class RuleError(TinyOlapError):
    """Raised when an rule function fails or is invalid."""
    pass


class InvalidCellAddressError(TinyOlapError):
    """Raised when an invalid cube cell idx_address is detected."""
    pass


class InvalidOperationError(TinyOlapError):
    """Raised when the invalid operation on a database object is executed."""
    pass


class CubeCreationError(TinyOlapError):
    """Raised when the creation of a cube."""
    pass


class DimensionInUseError(TinyOlapError):
    """Raised when the deletion of a dimension failed to to being used by a cube."""
    pass


class DatabaseFileError(TinyOlapError):
    """Raised when an error occurs while handling database files."""
    pass


class FatalError(TinyOlapError):
    """Raised when a fatal error occurs."""
    pass


class KeyNotFoundError(TinyOlapError):
    """Raised when a certain member, dimension, table etc. not exist."""
    pass


class InvalidKeyError(TinyOlapError):
    """Raised when a certain name of a member, dimension, table etc. is invalid  or not supported."""
    pass


class DuplicateKeyError(TinyOlapError):
    """Raised when a certain member, dimension, table etc. was added that already exists."""
    pass


class InvalidMemberNameError(TinyOlapError):
    """Raised when a dimension member name is invalid, containing unsupported special characters."""
    pass


class DimensionEditModeError(TinyOlapError):
    """Raised when an error occurred while a dimension is in edit mode,
    or if member were added, removed or renamed while not in edit mode.
    Call 'edit_begin()' to start editing."""
    pass
