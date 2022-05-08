import uuid
from datetime import datetime
from enum import Enum
import enum_tools

import tinyolap.config as config

enum_tools.documentation.INTERACTIVE = True


@enum_tools.documentation.document_enum
class UserRole(Enum):
    """Defines the user roles support by TinyOlap databases."""
    ADMIN = 0   # doc: (default role) Members of this role can perform all activities on the database.
    EDITOR = 1  # doc: Members of this role can modify write-enabled dimensions, create subsets and read and write data.
    WRITER = 2  # doc: Members of this role can read and write data.
    READER = 3  # doc: Members of this role can read data.


class User:
    def __init__(self, name:str, full_name: str= None, email: str = None):
        self._name = name
        self._full_name = full_name
        self._email = email

    @property
    def name(self) -> str:
        """Name of the user."""
        return self._name



class UserCollection:
    def __init__(self, database):
        self._admin_user_name = "admin"
        self.db = database
        self._users: dict = dict()
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


class UserSessionToken:
    """Represents a database session token for a specific user.
    Used for authenticated client side access."""

    def __init__(self, database: str, user: str):
        self._database_name = database
        self._user_name = user
        self._token: str = str(uuid.uuid4())

    @property
    def user(self) -> str:
        """Name of the user."""
        return self._user_name

    @property
    def database(self) -> str:
        """Name of the database the user is connected to."""
        return self._database_name

    @property
    def token(self) -> str:
        """Returns the session token."""
        return self._token

    def to_dict(self):
        return {"contentType": config.Config.ContentTypes.ATTRIBUTE,
                "version": config.Config.VERSION,
                "database": self._database_name,
                "user": self._user_name,
                "token": self._token,
                }

    def __str__(self):
        return self._token

    def __repr__(self):
        return self._token

class UserSession:
    pass

class UserSessionManager:
    def __init__(self, database):
        self._database = database
        self._sessions = dict()

    def create_token(self, user: User ) -> UserSessionToken:
        token = UserSessionToken(self._database.name, user.name)

        return token

    def validate(self, token) -> (bool, User):
        """
        Validates the user session token. A user session token is valid if it is available
        in the user session manager.

        :param token: The user session token to validate. Either as UserSessionToken object instance,
            or string containing a token id.
        :return: True if the token is valid, False otherwise.
        """
        if isinstance(token, UserSessionToken):
            token = token.token
        elif not isinstance(token, str):
            token= str(token)
        user = self._sessions.get(token.token, None)
        return bool(user), user
