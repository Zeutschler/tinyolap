# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations


class TinyOlapError(Exception):
    """Base class for all tinyOlap specific exceptions."""
    pass


class TinyOlapEncryptionError(TinyOlapError):
    """Raised when an encryption or decryption error occured. Especially on wrong password."""
    pass


class TinyOlapRuleError(TinyOlapError):
    """Raised when an rule function fails or is invalid."""
    pass


class TinyOlapInvalidAddressError(TinyOlapError):
    """Raised when an invalid cube cell idx_address is detected."""
    pass


class TinyOlapInvalidOperationError(TinyOlapError):
    """Raised when the invalid operation on a database object is executed."""
    pass


class TinyOlapCubeCreationError(TinyOlapError):
    """Raised when the creation of a cube."""
    pass


class TinyOlapDimensionInUseError(TinyOlapError):
    """Raised when the deletion of a dimension failed to to being used by a cube."""
    pass


class TinyOlapStorageError(TinyOlapError):
    """Raised when an error occurs while accessing or handling database storage_provider."""
    pass

class TinyOlapSerializationError(TinyOlapError):
    """Raised when an error occurs on serialization or deserialization of TinyOlap objects."""
    pass

class TinyOlapIOError(TinyOlapError):
    """Raised when an error occurs while accessing or handling files."""
    pass

class TinyOlapFatalError(TinyOlapError):
    """Raised when a fatal error occurs."""
    pass


class TinyOlapKeyNotFoundError(TinyOlapError):
    """Raised when a certain member, dimension, table etc. not exist."""
    pass


class TinyOlapInvalidKeyError(TinyOlapError):
    """Raised when a certain name of a member, dimension, table etc. is invalid  or not supported."""
    pass


class TinyOlapDuplicateKeyError(TinyOlapError):
    """Raised when a certain member, dimension, table etc. was added that already exists."""
    pass


class TinyOlapInvalidMemberNameError(TinyOlapError):
    """Raised when a dimension member name is invalid, containing unsupported special characters."""
    pass


class TinyOlapDimensionEditModeError(TinyOlapError):
    """Raised when an error occurred while a dimension is in edit mode,
    or if member were added, removed or renamed while not in edit mode.
    Call 'edit_begin()' to start editing."""
    pass
