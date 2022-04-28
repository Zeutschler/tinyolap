from enum import Enum
import enum_tools

enum_tools.documentation.INTERACTIVE = True


@enum_tools.documentation.document_enum
class UserRole(Enum):
    """Defines the user roles support by TinyOlap databases."""
    ADMIN = 0   # doc: (default role) Members of this role can perform all activities on the database.
    EDITOR = 1  # doc: Members of this role can modify write-enabled dimensions, create subsets and read and write data.
    WRITER = 2  # doc: Members of this role can read and write data.
    READER = 3  # doc: Members of this role can read data.


class User:
    pass

class UserCollection:
    def __init__(self, database):
        self._admin_user_name = "admin"
        self.db = database
        self._users: dict[User] = dict()
        self._users[self._admin_user_name] = User(self._admin_user_name)

    def __iter__(self):
        for user in self._users:
            yield user

class UserGroup:
    """Defines a group of users. Used for authorization management."""
    @property
    def name(self):
        return self._name

    @property
    def users(self) -> UserCollection:
        return self._users



