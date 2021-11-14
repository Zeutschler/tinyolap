# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

class TinyOlapException(Exception):
    """Base class for all tinyOlap specific exceptions."""
    pass


class RuleException(TinyOlapException):
    """Raised when an rule function fails or is invalid."""
    pass


class InvalidCellAddressException(TinyOlapException):
    """Raised when an invalid cube cell idx_address is detected."""
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


class DatabaseBackendException(TinyOlapException):
    """Raised when an error occurs while accessing or handling database storage_provider or files."""
    pass


class FatalException(TinyOlapException):
    """Raised when a fatal error occurs."""
    pass


class KeyNotFoundError(TinyOlapException):
    """Raised when a certain member, dimension, table etc. not exist."""
    pass


class InvalidKeyException(TinyOlapException):
    """Raised when a certain name of a member, dimension, table etc. is invalid  or not supported."""
    pass


class DuplicateKeyException(TinyOlapException):
    """Raised when a certain member, dimension, table etc. was added that already exists."""
    pass


class InvalidMemberNameError(TinyOlapException):
    """Raised when a dimension member name is invalid, containing unsupported special characters."""
    pass


class DimensionEditModeException(TinyOlapException):
    """Raised when an error occurred while a dimension is in edit mode,
    or if member were added, removed or renamed while not in edit mode.
    Call 'edit_begin()' to start editing."""
    pass
