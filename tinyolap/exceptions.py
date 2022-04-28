# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations


class TinyOlapError(BaseException):
    """Base class for all tinyOlap specific exceptions."""
    pass


class TinyOlapEncryptionError(BaseException):
    """Raised when an encryption or decryption error occured. Especially on wrong password."""
    pass


class TinyOlapRuleError(BaseException):
    """Raised when an rule function fails or is invalid."""
    pass


class TinyOlapInvalidAddressError(BaseException):
    """Raised when an invalid cube cell idx_address is detected."""
    pass


class TinyOlapInvalidOperationError(BaseException):
    """Raised when the invalid operation on a database object is executed."""
    pass


class TinyOlapCubeCreationError(BaseException):
    """Raised when the creation of a cube."""
    pass


class TinyOlapDimensionInUseError(BaseException):
    """Raised when the deletion of a dimension failed to to being used by a cube."""
    pass


class TinyOlapStorageError(BaseException):
    """Raised when an error occurs while accessing or handling database storage_provider."""
    pass

class TinyOlapSerializationError(BaseException):
    """Raised when an error occurs on serialization or deserialization of TinyOlap objects."""
    pass

class TinyOlapIOError(BaseException):
    """Raised when an error occurs while accessing or handling files."""
    pass

class TinyOlapFatalError(BaseException):
    """Raised when a fatal error occurs."""
    pass


class TinyOlapKeyNotFoundError(BaseException):
    """Raised when a certain member, dimension, table etc. not exist."""
    pass


class TinyOlapInvalidKeyError(BaseException):
    """Raised when a certain name of a member, dimension, table etc. is invalid  or not supported."""
    pass


class TinyOlapDuplicateKeyError(BaseException):
    """Raised when a certain member, dimension, table etc. was added that already exists."""
    pass


class TinyOlapInvalidMemberNameError(BaseException):
    """Raised when a dimension member name is invalid, containing unsupported special characters."""
    pass


class TinyOlapDimensionEditModeError(BaseException):
    """Raised when an error occurred while a dimension is in edit mode,
    or if member were added, removed or renamed while not in edit mode.
    """
    pass

class TinyOlapDimensionEditCircularReferenceError(BaseException):
    """Raised when an error occurred while a dimension is in edit mode,
    and a parent child relation will be created that would cause a circular reference.
    """
    pass
