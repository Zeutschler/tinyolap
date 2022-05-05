from __future__ import annotations

import json
import re
from collections.abc import Iterable
import enum_tools.documentation
import fnmatch

import tinyolap.config as config
import tinyolap.exceptions as exceptions
import tinyolap.dimension as dimension
import tinyolap.member as member
import tinyolap.utilities.case_insensitive_dict as cidict
import tinyolap.utilities.hybrid_dict as hdict
import tinyolap.utilities.utils as utils
enum_tools.documentation.INTERACTIVE = True


class AttributeField:
    """Represents a single attribute field of a dimension and provides access to
    the attribute values and the members associated wuith certain attribute values."""
    __slots__ = '_dimension', '_name', '_value_type', '_cache'

    def __init__(self, dimension: dimension.Dimension, name: str, value_type: type = None):
        self._dimension = dimension
        self._name = name
        self._value_type = value_type
        self._cache = cidict.CaseInsensitiveDict()

    def __repr__(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    def __getitem__(self, member):
        """Returns the attribute value of a member."""
        if type(member) is int:
            member = self._dimension.members[member]
        member = str(member)

        if member in self._cache:
            return self._cache[member]

        if member not in self._dimension._member_idx_lookup:
            raise KeyError(f"Failed to get member attribute value. "
                           f"'{member}' is not a member of dimension {self._dimension._name}.")
        idx = self._dimension._member_idx_lookup[member]
        if self._name not in self._dimension.member_defs[idx][self._dimension.ATTRIBUTES]:
            return None
        return self._dimension.member_defs[idx][self._dimension.ATTRIBUTES][self._name]

    def __setitem__(self, member, value):
        if value is not None:
            if self._value_type is not None:
                if not type(value) is self._value_type:
                    raise TypeError(f"Failed to set member attribute value. "
                                    f"Value is of type '{str(type(value))}' but type '{str(self._value_type)}' was expected.")
        if type(member) is int:
            member = self._dimension.members[member]
        member = str(member)
        if member not in self._dimension._member_idx_lookup:
            raise KeyError(f"Failed to set member attribute value. "
                           f"'{member}' is not a member of dimension {self._dimension._name}.")
        idx = self._dimension._member_idx_lookup[member]
        if value is not None:
            self._dimension.member_defs[idx][self._dimension.ATTRIBUTES][self._name] = value
        else:
            if self._name in self._dimension.member_defs[idx][self._dimension.ATTRIBUTES]:
                del self._dimension.member_defs[idx][self._dimension.ATTRIBUTES][self._name]

        self._cache[member] = value

    def __delitem__(self, member):
        if type(member) is int:
            member = self._dimension.members[member]
        member = str(member)
        if member not in self._dimension._member_idx_lookup:
            raise KeyError(f"Failed to delete member attribute value. "
                           f"'{member}' is not a member of dimension {self._dimension._name}.")
        idx = self._dimension._member_idx_lookup[member]
        if self._name in self._dimension.member_defs[idx][self._dimension.ATTRIBUTES]:
            del self._dimension.member_defs[idx][self._dimension.ATTRIBUTES][self._name]

        self._cache[member] = None

    def clear(self):
        """Clears all attribute values for all members of the dimension."""
        self._cache = dict()
        for member in self._dimension.members:
            del self._dimension.member_defs[member.index][self._dimension.ATTRIBUTES][self._name]

    def set(self, member, value):
        """
        Sets the attribute value for a specific member.
        :param member: The member to set the attribute value for.
        :param value: The value to get set
        """
        self.__setitem__(member, value)

    def get(self, member):
        """
        Returns the attribute value for a specific member.
        :param member: The member to return the attribute value for.
        :returns: The value to of attribute. If the value is not set, None will be returned.
        """
        self.__getitem__(member)

    def filter(self, value_or_pattern, case_sensitive: bool = False) -> member.MemberList:
        """Provides value search or wildcard pattern matching and filtering on the attribute values of members
         and return a list of matching members. Note: Wildcard matching is only available is the value type of the
         attribute is of type 'str', for all other value-types an equality check (a == b) will be applied.

            * * matches everything
            * ? matches any single character
            * [seq] matches any character in seq
            * [!seq] matches any character not in seq

        :param value_or_pattern: The value or wildcard pattern to filter the member attribute values for.
        :param case_sensitive: Identifies if matching on string attributes should be case-sensitive.
        :return: The filtered member list.
        """
        if self._value_type is str:
            if type(value_or_pattern) is str:
                if case_sensitive:
                    value_or_pattern = value_or_pattern.lower()
                    if any((c in '*?[]') for c in value_or_pattern):
                        return member.MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                           fnmatch.fnmatch(v.lower(), value_or_pattern)])
                    else:
                        return member.MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            v.lower() == value_or_pattern])
                else:
                    if any((c in '*?[]') for c in value_or_pattern):
                        return member.MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            fnmatch.fnmatch(v, value_or_pattern)])
                    else:
                        return member.MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            v == value_or_pattern])

        return member.MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                            v == value_or_pattern])

    def match(self, regular_expression) -> member.MemberList:
        """Provides regular expression pattern matching and filtering on the attributes values of members
        and return a list of matching members.

        :param regular_expression: The regular expression or a valid regular expression string to filter the member list.
        :return: The filtered member list.
        """
        if type(regular_expression) is not re:
            regular_expression = re.compile(regular_expression)
        return member.MemberList(self._dimension,
                          [self._dimension.members[k] for k,v in self._cache.items() if regular_expression.search(v)])

    def _flush(self):
        """Flushes the internal cache of the AttributeField.
        Flushing the cache is required when the dimension gets updated (edit -> commit)."""
        self._cache = dict()

        # rebuild the cache
        for idx in self._dimension._member_idx_lookup:
            if self._name in self._dimension.member_defs[idx][self._dimension.ATTRIBUTES]:
                self._cache[self._dimension.member_defs[idx][self._dimension.NAME]] =\
                    self._dimension.member_defs[idx][self._dimension.ATTRIBUTES][self.name]
            else:
                self._cache[self._dimension.member_defs[idx][self._dimension.NAME]] = None

    @property
    def dimension(self) -> dimension.Dimension:
        """Returns the parent dimension of the attribute field."""
        return self._dimension

    @property
    def name(self) -> str:
        """Returns the name of the attribute field."""
        return self._name

    @property
    def value_type(self) -> type:
        """Returns the defined value type of the attribute field."""
        return self._value_type

    @property
    def values(self) -> tuple:
        """Returns a list of all the attribute values."""
        distinct = set(self._cache.values())
        if None in distinct:
            distinct.remove(None)  # remove the None value, it's not a relevant attribute value
        return tuple(distinct)

    def to_dict(self) -> dict:
        """FOR INTERNAL USE! Converts the contents of the attribute field to a dict."""
        return {"contentType": config.Config.ContentTypes.ATTRIBUTE,
                "version": config.Config.VERSION,
                "dimension": self._dimension.name,
                "name": self._name,
                "valueType": str(self._value_type),
                "values": [{"member": k, "value": v} for k, v in self._cache.items()]
                }

    def from_dict(self, data: dict) -> AttributeField:
        """FOR INTERNAL USE! Populates the contents of the attribute field from a dict."""
        self.clear()
        try:
            utils.check_content_type_and_version(data["contentType"], data["version"], config.Config.ContentTypes.ATTRIBUTE)

            self._name = data["name"]
            if not data["valueType"] in config.Config.BUILTIN_VALUE_TYPES:
                raise exceptions.TinyOlapSerializationError(f"Failed to deserialize attribute '{self.name}' "
                                                 f"of dimension '{self._dimension.name}'. Unsupported "
                                                 f"value type '{data['valueType']}' found.")
            self._value_type = config.Config.BUILTIN_VALUE_TYPES[data["valueType"]]

            # read all available values
            for kvp in data["values"]:
                member = kvp["member"]
                value = kvp["value"]
                self.__setitem__(member, value)

        except Exception as e:
            raise exceptions.TinyOlapSerializationError(
                f"Failed to deserialize '{config.Config.ContentTypes.ATTRIBUTE}'. "
                                             f"{str(e)}")
        return self

    def to_json(self, prettify: bool = False) -> str:
        """FOR INTERNAL USE! Converts the contents of the attribute field to a json string."""
        return json.dumps(self.to_dict(), indent=(2 if prettify else None))

    def from_json(self, attribute_as_json_string: str) -> AttributeField:
        """FOR INTERNAL USE! Populates the contents of the attribute field from a json string."""
        self.from_dict(json.loads(attribute_as_json_string))
        return self


class Attributes(Iterable[AttributeField]):
    """Represents the list of member attributes available in a dimension."""
    __slots__ = '_dimension', '_fields'

    def __init__(self, parent: dimension.Dimension):
        self._dimension: dimension.Dimension = parent
        self._fields: hdict.HybridDict[AttributeField] = \
            hdict.HybridDict[AttributeField](source=parent)

    def __getitem__(self, item) -> AttributeField:
        """
        Returns an attribute by name or index.
        :param item: Name or index of the attribute to be returned.
        :return: The requested attribute.
        """
        return self._fields[item]

    def __contains__(self, item):
        return item in self._fields

    def __setitem__(self, item, value):
        self._fields[item] = value

    def __len__(self):
        return len(self._fields)

    def __iter__(self):
        for attribute in self._fields:
            yield attribute

    def clear(self):
        """ Clears (deletes) all attributes defined for the dimension."""
        self._fields.clear()

    def remove(self, attribute):
        if attribute in self._fields:
            self._fields.remove(attribute)

    def add(self, name:str, value_type: type = None) -> AttributeField:
        if not utils.is_valid_db_object_name(name):
            raise exceptions.TinyOlapInvalidKeyError(f"'{name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters, hyphen and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if name in self._fields:
            raise exceptions.TinyOlapDuplicateKeyError(f"Failed to add attribute to dimension. "
                                        f"An attribute named '{name}' already exists.")

        attribute = AttributeField(dimension=self._dimension, name=name, value_type=value_type)
        self._fields.append(attribute)
        return attribute

    def get(self, attribute: str, member):
        """
        Returns the attribute value for a specific attribute and member.
        :param attribute: The name of the attribute to be returned.
        :param member: The member to return the attribute value for.
        :return: An attribute value.
        """
        try:
            return self._fields[attribute][member]
        except Exception as e:
            raise exceptions.TinyOlapInvalidKeyError(f"Failed to access member attribute "
                                      f"'{attribute}' for member '{member}'. "
                                          + str(e))

    def set(self, attribute: str, member, value):
        """
        Sets the attribute value for a specific attribute and member.
        :param attribute: The name of the attribute to be set.
        :param member: The member to set the attribute value for.
        :param value: The value to be set.
        """
        try:
            self._fields[attribute][member] = value
        except Exception as e:
            raise exceptions.TinyOlapInvalidKeyError(f"Failed to access member attribute "
                                      f"'{attribute}' for member '{member}'. "
                                          + str(e))

    def to_dict(self) -> dict:
        """FOR INTERNAL USE! Converts the contents of the dimension attributes to a dict."""
        return {"contentType": config.Config.ContentTypes.ATTRIBUTES,
                "version": config.Config.VERSION,
                "dimension": self._dimension.name,
                "attributes": [a.to_dict() for a in self._fields]
                }

    def from_dict(self, data: dict) -> Attributes:
        """FOR INTERNAL USE! Populates the contents of the dimension attributes from a dict."""
        self.clear()
        try:
            utils.check_content_type_and_version(data["contentType"], data["version"],
                                           config.Config.ContentTypes.ATTRIBUTES)

            # read all available attributes
            for attribute_data in data["attributes"]:
                attribute = AttributeField(dimension=self._dimension, name="_").from_dict(attribute_data)
                self._fields.append(attribute)

        except Exception as e:
            raise exceptions.TinyOlapSerializationError(
                f"Failed to deserialize '{config.Config.ContentTypes.ATTRIBUTES}'. "
                                             f"{str(e)}")
        return self

    def to_json(self, prettify: bool = False) -> str:
        """FOR INTERNAL USE! Converts the contents of the dimension attributes to a json string."""
        return json.dumps(self.to_dict(), indent=(2 if prettify else None))

    def from_json(self, attributes_as_json_string: str):
        """FOR INTERNAL USE! Populates the contents of the dimension attributes from a json string."""
        self.from_dict(json.loads(attributes_as_json_string))
