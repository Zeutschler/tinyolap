# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

class Role:
    pass


class Viewer(Role):
    """
    Permissions for read-only actions that do not affect state of a database,
    such as reading (but not modifying) data from cubes.
    """
    pass


class Editor(Role):
    """
    All viewer permissions, plus permissions to modify data in cubes, such as writing
    values to cubes, splashing of values over cubes, importing data and using the history.
    """
    pass


class Owner(Role):
    """
    All editor permissions, plus permissions to modify the structure of the database,
    such adding/modifying/removing of dimension, subsets, attributes, cubes and rules.
    """
    pass


class Admin(Role):
    """All owner permissions, plus permission to add/modify/remove users and roles."""
    pass


class User:
    def __init__(self, name: str, password: str = None, role: Role = Admin()):
        self._name = name
        self._password = password
        self._role = role

    @property
    def name(self) -> str:
        return self._name

    def rename(self, new_name: str):
        self._name = new_name


    @property
    def role(self) -> Role:
        return self._role

    @role.setter
    def role(self, value: Role):
        self._role = value

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, value: str):
        self._password = value
