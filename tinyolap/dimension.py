# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in
# the LICENSE file in the root directory of this source tree.

from __future__ import annotations
import importlib
from collections.abc import Iterable, Sequence
import inspect
from abc import ABC, abstractmethod
import fnmatch
import json
from abc import abstractmethod
from typing import Any

from tinyolap.config import Config
from tinyolap.storage.storageprovider import StorageProvider
from tinyolap.member import Member, MemberList
from tinyolap.exceptions import *
from tinyolap.utilities.utils import *
from tinyolap.utilities.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.utilities.hybrid_dict import HybridDict


class AttributeField:
    """Represents a single attribute field of a dimension and provides access to
    the attribute values and the members associated wuith certain attribute values."""

    def __init__(self, dimension: Dimension, name: str, value_type: type = None):
        self._dimension = dimension
        self._name = name
        self._value_type = value_type
        self._cache = CaseInsensitiveDict()

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
            del self._dimension.member_defs[member.idx][self._dimension.ATTRIBUTES][self._name]

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

    def filter(self, value_or_pattern, case_sensitive: bool = False) -> MemberList:
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
                        return MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            fnmatch.fnmatch(v.lower(), value_or_pattern)])
                    else:
                        return MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            v.lower() == value_or_pattern])
                else:
                    if any((c in '*?[]') for c in value_or_pattern):
                        return MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            fnmatch.fnmatch(v, value_or_pattern)])
                    else:
                        return MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                                            v == value_or_pattern])

        return MemberList(self._dimension, [self._dimension.member(k) for k, v in self._cache.items() if
                                            v == value_or_pattern])

    def match(self, regular_expression) -> MemberList:
        """Provides regular expression pattern matching and filtering on the attributes values of members
        and return a list of matching members.

        :param regular_expression: The regular expression or a valid regular expression string to filter the member list.
        :return: The filtered member list.
        """
        if type(regular_expression) is not re:
            regular_expression = re.compile(regular_expression)
        return MemberList(self._dimension,
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
    def dimension(self) -> Dimension:
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
        return {"contentType": Config.ContentTypes.ATTRIBUTE,
                "version": Config.VERSION,
                "dimension": self._dimension.name,
                "name": self._name,
                "valueType": str(self._value_type),
                "values": [{"member": k, "value": v} for k, v in self._cache.items()]
                }

    def from_dict(self, data: dict) -> AttributeField:
        """FOR INTERNAL USE! Populates the contents of the attribute field from a dict."""
        self.clear()
        try:
            check_content_type_and_version(data["contentType"], data["version"], Config.ContentTypes.ATTRIBUTE)

            self._name = data["name"]
            if not data["valueType"] in Config.BUILTIN_VALUE_TYPES:
                raise TinyOlapSerializationError(f"Failed to deserialize attribute '{self.name}' "
                                                 f"of dimension '{self._dimension.name}'. Unsupported "
                                                 f"value type '{data['valueType']}' found.")
            self._value_type = Config.BUILTIN_VALUE_TYPES[data["valueType"]]

            # read all available values
            for kvp in data["values"]:
                member = kvp["member"]
                value = kvp["value"]
                self.__setitem__(member, value)

        except Exception as e:
            raise TinyOlapSerializationError(f"Failed to deserialize '{Config.ContentTypes.ATTRIBUTE}'. "
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
    def __init__(self, dimension: Dimension):
        self._dimension: Dimension = dimension
        self._fields: HybridDict[AttributeField] = HybridDict[AttributeField](source=dimension)

    def __getitem__(self, item) -> AttributeField:
        return self._fields[item]

    def __len__(self):
        return len(self._fields)

    def __iter__(self):
        for attribute in self._fields:
            yield attribute

    def clear(self):
        """ Clears (deletes) all attributes defined for the dimension."""
        self._fields.clear()

    def add(self, name:str, value_type: type = None) -> AttributeField:
        if not is_valid_db_object_name(name):
            raise TinyOlapInvalidKeyError(f"'{name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters, hyphen and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if name in self._fields:
            raise TinyOlapDuplicateKeyError(f"Failed to add attribute to dimension. "
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
            raise TinyOlapInvalidKeyError(f"Failed to access member attribute "
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
            raise TinyOlapInvalidKeyError(f"Failed to access member attribute "
                                      f"'{attribute}' for member '{member}'. "
                                          + str(e))

    def to_dict(self) -> dict:
        """FOR INTERNAL USE! Converts the contents of the dimension attributes to a dict."""
        return {"contentType": Config.ContentTypes.ATTRIBUTES,
                "version": Config.VERSION,
                "dimension": self._dimension.name,
                "attributes": [a.to_dict() for a in self._fields]
                }

    def from_dict(self, data: dict) -> Attributes:
        """FOR INTERNAL USE! Populates the contents of the dimension attributes from a dict."""
        self.clear()
        try:
            check_content_type_and_version(data["contentType"], data["version"], Config.ContentTypes.ATTRIBUTES)

            # read all available attributes
            for attribute_data in data["attributes"]:
                attribute = AttributeField(dimension=self._dimension, name="_").from_dict(attribute_data)
                self._fields.append(attribute)

        except Exception as e:
            raise TinyOlapSerializationError(f"Failed to deserialize '{Config.ContentTypes.ATTRIBUTES}'. "
                                             f"{str(e)}")
        return self

    def to_json(self, prettify: bool = False) -> str:
        """FOR INTERNAL USE! Converts the contents of the dimension attributes to a json string."""
        return json.dumps(self.to_dict(), indent=(2 if prettify else None))

    def from_json(self, attributes_as_json_string: str):
        """FOR INTERNAL USE! Populates the contents of the dimension attributes from a json string."""
        self.from_dict(json.loads(attributes_as_json_string))


class Subset(Iterable[Member]):
    """Subsets are static or dynamic lists of members from a dimension. They are useful for
    slicing and dicing cube and reporting purposes as well as to implement additional
    static or dynamic aggregations."""

    def __init__(self, dimension: Dimension, name: str, volatile: bool, *args):
        """
        FOR INTERNAL PURPOSE ONLY! DO NOT CREATE SUBSETS DIRECTLY, ALWAYS USE THE 'SUBSETS' PROPERTY PROVIDED
        THROUGH DIMENSION OBJECTS!

        Initializes a subset based on (a) single list of members, (b) a sequence of 'attribute name',
        'attribute value_or_pattern' argument pairs or (c) a single callback function.

        :param dimension: The dimension to create the subset for.
        :param name: The name of the subset to be created.
        :param volatile: Identifies if the subset is volatile, meaning requires runtime refresh.
        :param args: The arguments provided to set up the subset.
        """
        if not is_valid_db_object_name(name):
            raise TinyOlapInvalidKeyError(f"'{name}' is not a valid dimension subset name. "
                                      f"Lower case alphanumeric characters, hyphen and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        self._dimension: Dimension = dimension
        self._name: str = name
        self._volatile: bool = volatile
        self._attributes = None
        self._callable_function = None
        self._members = None

        if (len(args) == 1) and isinstance(args[0], Sequence):
            # static subset defined by a list of members

            # validate Member objects
            for member in args[0]:
                if type(member) is Member:
                    if member.dimension is not self._dimension:
                        raise TypeError(f"Failed to initialize static subset '{self._name}' from member list. "
                                        f"At least one member ('{member.name}') is not a member of the parent "
                                        f"dimension '{self._dimension.name} but from "
                                        f"dimension {member.dimension.name}.")

            self._members: HybridDict[Member] = \
                HybridDict[Member](items=[m if type(m) is Member else dimension.member(str(m)) for m in args[0]],
                                   source=dimension)

        elif (len(args) == 1) and callable(args[0]):
            # dynamic subset evaluated through a callable function
            self._callable_function = args[0]
            # check signature for number of arguments
            callable_args_count = len(inspect.signature(self._callable_function).parameters.keys())
            if 2 != callable_args_count:
                raise TypeError(f"The provided callable function '{self._callable_function.__name__}' "
                                f"requires {callable_args_count} arguments, but a "
                                f"callable function with 2 arguments was expected. "
                                f"The expected signature looks like this: "
                                f"'some_function(dimension, subset_name) -> Iterable|List|Tuple|Set'")

        elif (len(args) > 0) and (len(args) % 2 == 0):
            # dynamic subset evaluated through an attribute query.
            it = iter(args)                 # convert something like this ['att', 'value', 'att', 'value', ...]
            self._attributes = zip(it, it)  # ...to something like this [('att', 'value'), ('att', 'value'), ...]

        elif len(args) == 1 and type(args[0]) is Subsets:
            # Note: this only happens on deserialization
            pass
        else:
            raise TypeError(f"The arguments provide to method '__init__(...)' of class 'Subset'"
                            f"do not match the requirements: (a) single list of members, "
                            f"(b) a sequence of 'attribute name' and 'attribute value_or_pattern' argument pairs or "
                            f"(c) a single callback function.")

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name

    def __iter__(self):
        self._refresh()
        for member in self._members:
            yield member

    def __len__(self) -> int:
        return len(self._members)

    @property
    def members(self) -> HybridDict[Member]:
        """Returns the list of members in the subset."""
        self._refresh()
        return self._members

    def _refresh(self):
        """Refreshes the member list, if required."""
        if self._volatile:
            # refresh contents
            if self._callable_function:
                try:
                    members = self._callable_function(self._dimension, self._name)
                except Exception as e:
                    raise TinyOlapRuleError(f"Error on calling custom subset function "
                                            f"'{self._callable_function.__name__}'. {str(e)}")

                self._members = HybridDict[Member](
                    items=[m if type(m) is Member else self._dimension.member(str(m)) for m in members],
                    source=self._dimension)

            elif self._attributes:
                result = None
                members = self._dimension.members
                for attribute, value in self._attributes:
                    matches = set(self._dimension.attributes[attribute].filter(value))
                    if result is None:
                        result = matches
                    else:
                        result.intersection(matches)
                        if not result:
                            self._members = HybridDict[Member](items=[], source=self._dimension) # empty subset
                            return
                self._members = HybridDict[Member](items=list(result), source=self._dimension) # empty subset

    def to_dict(self, members_only: bool = False) -> dict:
        """
        Converts the subset into a dict, representing the subset definition and members of the subset.
        The subset can afterwards be restored using the 'from_dict(...)' function.
        :param members_only: Defines if the dict should only contain the members of the subset, and not it's definition.
        :return: The generated json string.
        """
        data = {"contentType": Config.ContentTypes.SUBSET,
                "version": Config.VERSION,
                "dimension": self._dimension.name,
                "name": self._name,
                "volatile": self._volatile,
                }
        if not members_only:
            callable_function_module = None
            callable_function = None
            if self._callable_function:
                callable_function_module = str(inspect.getmodule(self._callable_function))
                callable_function = self._callable_function.__name__
            data["callableFunctionModule"] = callable_function_module
            data["callableFunction"] = callable_function

            data["attributeQuery"] = self._attributes

        data["members"] = [m for m in self.members]
        return data

    def from_dict(self, data: dict) -> Subset:
        """
        **FOR INTERNAL USE!** Loads the subset from a dict object,
        normally created by the use of the 'to_dict(...)' function.

        :param data: The dict object to read from.
        """
        try:
            check_content_type_and_version(data["contentType"], data["version"], Config.ContentTypes.SUBSET)

            self._name = data["name"]
            self._volatile = data["volatile"]

            # (try to) instantiate the callable function
            callable_function_module = data["callableFunctionModule"]
            callable_function = data["callableFunction"]
            if callable_function:
                # let's try to initialize the function.
                try:
                    module = importlib.import_module(callable_function_module)
                    function = getattr(module, callable_function)
                    self._callable_function = function
                except Exception as e:
                    raise TinyOlapSerializationError(f"Failed to re-instantiate function "
                                                     f"'{callable_function}' form module "
                                                     f"'{callable_function_module}'. {str(e)}")

            # restore the attribute query definition
            self._attributes = data["attributeQuery"]

            # finally, restore the saved members that eblogn to the subset.
            self._members = HybridDict[Member](source=self._dimension, items=[m for m in data["members"]])

        except Exception as e:
            raise TinyOlapSerializationError(f"Failed to deserialize '{Config.ContentTypes.ATTRIBUTE}'. "
                                             f"{str(e)}")
        return self

    def to_json(self, members_only: bool = False, prettify: bool = False) -> str:
        """
        **FOR INTERNAL USE!** Converts the subset into a json string, representing the subset definition and members of the subset.
        The subset can afterwards be restored using the 'from_json(...)' function.
        :param members_only: Defines if the dict should only contain the members of the subset, and not it's definition.
        :param prettify: Defines if the json file should be prettified, using linebreaks and indentation (of 2).
        :return: The generated json string.
        """
        return json.dumps(self.to_dict(members_only), indent=(2 if prettify else None))

    def from_json(self, subset_as_json_string: str) -> Subset:
        """**FOR INTERNAL USE!** Loads the subset from a json string.
        Normally created by the use of the 'to_json(...)' function

        :param subset_as_json_string: The json string to read from.
        """
        return self.from_dict(json.loads(subset_as_json_string))


class Subsets(Sequence[Subset]):
    """Represents the list of members subsets available in a dimension."""
    def __init__(self, dimension: Dimension):
        self._dimension: Dimension = dimension
        self._subsets: HybridDict[Subset] = HybridDict[Subset](source=dimension)

    def __getitem__(self, item) -> Subset:
        return self._subsets.__getitem__(item)

    def __len__(self):
        return len(self._subsets)

    def __iter__(self):
        for subset in self._subsets:
            yield subset

    def __delitem__(self, key):
        del self._subsets[key]

    @property
    def dimension(self) -> Dimension:
        """
        Returns the parent dimension of the subset list.
        """
        return self._dimension

    def clear(self) -> Subsets:
        """
        Removes all subsets from the subset list.
        :return: The subset list itself.
        """
        self._subsets: HybridDict[Subset] = HybridDict[Subset](source=self._dimension)
        return self

    def remove(self, subset) -> Subsets:
        """
        Removes a specific subset from the list of subsets.
        :param subset: The subset or the name of the subset to be removed.
        :return: The subset list itself.
        """
        del self._subsets[subset]
        return self

    def add_static_subset(self, name: str, members) -> Subset:
        """
        Add a static member subset based on a list of members to the dimension.
        :param name: The name of the subset to be created.
        :param members: The list of members to be contained in the subset.
        :return: Returns the added created subset.
        """
        if name in self._subsets:
            raise TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
                                        f"A subset named '{name}' already exists.")

        subset = Subset(self._dimension, name, False, members)
        self._subsets.append(subset)
        return subset

    def add_attribute_subset(self, name: str, *args) -> Subset:
        """
        Adds a dynamic member subset based on a pair-wise sequence of 'attribute name' and
        'attribute value_or_pattern' arguments used for filtering members. If multiple filters
        have been defined, then the resulting subset will contain only those members that match
        all filter conditions. If the value_or_pattern arguments contain any of wildcard
        characters '*?[]', then a wildcard serach will be applied, otherwise a case-insensitive
        string comparison will be executed.

        Alternatively, the second argument can be a
        callable function with the following signature 'somefunction(attribute_value) -> bool:'.
        If such a function returns ´´True´´ for a given attribute value, then the associated member
        will be contained in the subset, otherwise then member will be excluded.

        .. code:: python
            # attribute subsets based fixed values for attributes.
            dim.subsets.add_attribute_subset("my-subset", "color", "green")  # valid
            dim.subsets.add_attribute_subset("my-subset", "color", "green", "weight", 400.0)  # valid
            dim.subsets.add_attribute_subset("my-subset", "just-on-argument")  # invalid

            # attribute subsets based on a callable function.
            def black_or_blue(value):
                return value in ["black", "blue"]
            dim.subsets.add_attribute_subset("my-subset", "color", black_or_blue)  # valid

        :param name: The name of the subset to be created.

        :param args: A paired sequence of 'attribute name', 'attribute value_or_pattern' or
            callable function arguments.
        """
        if name in self._subsets:
            raise TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
                                        f"A subset named '{name}' already exists.")

        subset = Subset(self._dimension, name, True, *args)
        self._subsets.append(subset)
        return subset

    def add_custom_subset(self, name: str, callback: callable, volatile: bool = False) -> Subset:
        """
        Add a dynamic member subset based on a callback function which will need to take
        2 arguments and return a sequence (e.g. a list) of members or just member names.

        .. code:: python
            # the function to be called.
            def custom_evaluator(dimension: Dimension, subset_name: str) -> list:
                if subset == "random"
                    # return 10 random members from the dimension
                    return random.sample(dimension.members, 10)
                else:
                    return [m for m in dimension.members if m.name.startswith("T")]

            # add 2 subsets using the function.
            dim.subsets.add_custom_subset("random", custom_evaluator)
            dim.subsets.add_custom_subset("other", custom_evaluator)

        :param name: The name of the subset to be created.

        :param callback: A callable function with signature 'somefunction(dimension, subset_name) -> Sequence'

        :param volatile: Identifies that the function need to be evaluated on every call of the subset.
        """
        if name in self._subsets:
            raise TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
                                        f"A subset named '{name}' already exists.")

        subset = Subset(self._dimension, name, volatile, callback)
        self._subsets.append(subset)
        return subset

    def to_dict(self, members_only: bool = False) -> dict:
        """
        **FOR INTERNAL USE!** Converts the subsets into a dict, representing all subset definitions and members.
        The subsets can afterwards be restored using the 'from_dict(...)' function.

        :param members_only: Defines if the dict should only contain the members of the subset, and not it's definition.
        :return: The generated json string.
        """
        return {"contentType": Config.ContentTypes.SUBSETS,
                "version": Config.VERSION,
                "dimension": self._dimension.name,
                "subsets": [a.to_dict() for a in self._subsets]
                }

    def from_dict(self, data: dict) -> Subsets:
        """
        **FOR INTERNAL USE!** Loads the subsets from a dict object,
        normally created by the use of the 'to_dict(...)' function.

        :param data: The dict object to read from.
        """
        self.clear()
        try:
            check_content_type_and_version(data["contentType"], data["version"], Config.ContentTypes.SUBSETS)

            # read all available attributes
            for subset_data in data["subsets"]:
                subset = Subset(self._dimension,  # the 'self' argument indicates deserialization
                                "_", False, self).from_dict(subset_data)
                self._subsets.append(subset)

        except Exception as e:
            raise TinyOlapSerializationError(f"Failed to deserialize '{Config.ContentTypes.SUBSETS}'. "
                                             f"{str(e)}")
        return self

    def to_json(self, members_only: bool = False, prettify: bool = False) -> str:
        """
        **FOR INTERNAL USE!** Converts the subsets into a json string, representing all subset definitions and members.
        The subsets can afterwards be restored using the 'from_json(...)' function.

        :param members_only: Defines if the dict should only contain the members of the subset, and not it's definition.
        :param prettify: Defines if the json file should be prettified, using linebreaks and indentation (of 2).
        :return: The generated json string.
        """
        return json.dumps(self.to_dict(members_only), indent=(2 if prettify else None))

    def from_json(self, subsets_as_json_string: str):
        """**FOR INTERNAL USE!** Loads the subsets from a json string.
        Normally created by the use of the 'to_json(...)' function

        :param subsets_as_json_string: The json string to read from.
        """
        self.from_dict(json.loads(subsets_as_json_string))

class Dimension:
    """
    Dimensions are used to define the axis of a multi-dimensional :ref:`cube <cubes>`.
    Dimensions contain a list or hierarchy of :ref:`member_defs <member_defs>`.
    Members are string address and representing the entities of the dimension. e.g.,
    for a dimension called 'months' this would be the month names 'Jan' to 'Dec' or
    month aggregations like quarters or semesters.

    .. important::
        It is not foreseen to create *Dimension* objects directly! Always use the ``add_dimension()``
        method of a :ref:`database <databases>` to create a new dimension instance,
        as shown in the code fragment below.

        .. code:: python

            from tinyolap.database import Database

            # setup a new database
            database = Database("foo")

            # define dimensions
            dimension = db.add_dimension("bar")

    Within a single database, dimensions need to be unique by there name.
    """

    class MemberIndexManager:
        """
        Manages the available member index numbers.
        """

        def __init__(self, current: list[int] = None, first_free: int = 1):
            self.free: set[int] = set()
            self.next_new = max(1, first_free)
            if current:
                all_members = set(range(max(current) + 1))
                used_members = set(current)
                self.free: all_members - used_members
                self.next_new = max(current) + 1

        def clear(self):
            self.free: set[int] = set()
            self.next_new = 1

        def pop(self) -> int:
            if self.free:
                return self.free.pop()
            index = self.next_new
            self.next_new += 1
            return index

        def push(self, index):
            if type(index) is int:
                self.free.add(index)
            elif isinstance(index, Sequence):
                self.free.update(index)
            else:
                raise ValueError()

    __magic_key = object()

    @classmethod
    def _create(cls, storage_provider: StorageProvider, name: str, description: str = ""):
        """
        NOT INTENDED FOR EXTERNAL USE! Creates a new dimension.

        :param storage_provider: The storage provider of the database.
        :param name: Name of the dimension to be created.
        :param description: Description of the dimension to be added.
        :return: The new dimension.
        """
        dimension = Dimension(Dimension.__magic_key, name, description)
        dimension._storage_provider = storage_provider
        if storage_provider and storage_provider.connected:
            storage_provider.add_dimension(name, dimension.to_json())
        return dimension

    IDX = 0
    NAME = 1
    DESC = 2
    PARENTS = 3
    CHILDREN = 4
    ALL_PARENTS = 5
    LEVEL = 6
    ATTRIBUTES = 7
    BASE_CHILDREN = 8
    ALIASES = 9
    FORMAT = 10

    MEMBERS = 3
    IDX_MEMBERS = 4

    def __init__(self, dim_creation_key, name: str, description: str = ""):
        """
        NOT INTENDED FOR DIRECT USE! Cubes and dimensions always need to be managed by a Database.
        Use method 'Database.add_cube(...)' to create objects type Cube.

        :param dim_creation_key:
        :param name:
        :param description:
        """
        assert (dim_creation_key == Dimension.__magic_key), \
            "Objects of type Dimension can only be created through the method 'Database.add_dimension()'."

        self._name: str = name.strip()
        self.description: str = description
        self.member_defs: dict[int, dict] = {}
        self._member_idx_manager = Dimension.MemberIndexManager()
        self._member_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self._member_idx_list = []
        self.member_counter = 0
        self.highest_idx = 0
        self._members = None

        self.database = None
        self._storage_provider: StorageProvider = None
        self.edit_mode: bool = False
        self.recovery_json = ""
        self.recovery_idx = set()

        self.alias_idx_lookup: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()

        # New Attributes
        self._attributes: Attributes = Attributes(self)
        # OLD Attributes
        self._attributes_dict: CaseInsensitiveDict[str, int] = CaseInsensitiveDict()
        self.attribute_query_caching: bool = True
        self.attribute_cache: CaseInsensitiveDict[str, list[str]] = CaseInsensitiveDict()

        # New Subsets
        self._subsets: Subsets = Subsets(self)
        # OLD Subsets
        self._dict_subsets: CaseInsensitiveDict[str, dict] = CaseInsensitiveDict()
        self._subset_idx_manager = Dimension.MemberIndexManager()

    def __str__(self):
        """Returns the string representation of the dimension."""
        return f"dim:{self._name}"

    def __repr__(self):
        """Returns the string representation of the dimension."""
        return f"dim{self._name}"

    def __len__(self):
        """Returns the length (number of member_defs) of the dimension"""
        return len(self.member_defs)

    # region Member accesses by name or index
    def __getitem__(self, item):
        """
        Returns the Member object for a given name or member index.
        :param item: The Member objects name or index.
        :return: The member object.
        """
        return self.member(item)
    # endregion


    @property
    def name(self) -> str:
        """Returns the name of the dimension."""
        return self._name

    @property
    def description(self) -> str:
        """Returns the description of the dimension."""
        return self._description

    @description.setter
    def description(self, value: str):
        """Sets the description of the dimension."""
        self._description = value

    @property
    def attributes(self) -> Attributes:
        """Returns the member attributes defined for the dimension."""
        return self._attributes

    @property
    def subsets(self) -> Subsets:
        """Returns the member attributes defined for the dimension."""
        return self._subsets

    # region Dimension editing
    def clear(self) -> Dimension:
        """
        Deletes all member_defs and all member_defs from the dimension. Attributes will be kept.

        :return: The dimension itself.
        """
        self._member_idx_lookup = CaseInsensitiveDict()
        self.member_defs = {}
        self._member_idx_manager.clear()
        self.alias_idx_lookup.clear()
        self.member_counter = 0
        self._dict_subsets = {}
        self._subset_idx_manager.clear()
        return self

    def edit(self) -> Dimension:
        """
        Sets the dimension into edit mode. Required to add, remove or rename member_defs,
        to add remove or edit subsets or attributes and alike.

        :return: The dimension itself.
        """
        if self.edit_mode:
            raise TinyOlapDimensionEditModeError("Failed to set edit mode. 'edit_begin()' was already called before.")
        self.edit_mode = True
        self.recovery_json = self.to_json()
        self.recovery_idx = set(self._member_idx_lookup.values())
        return self

    def commit(self) -> Dimension:
        """
        Commits all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        self.__update_member_hierarchies()
        if self._storage_provider and self._storage_provider.connected:
            self._storage_provider.add_dimension(self._name, self.to_json())

        # remove data for obsolete member_defs (if any) from database
        obsolete = self.recovery_idx.difference(set(self._member_idx_lookup.values()))
        if obsolete:
            self.database._remove_members(self, obsolete)
        # update member list
        self._member_idx_list = [idx for idx in self.member_defs.keys()]

        # update the member list
        self._members = MemberList(self, [
            Member(dimension=self, member_name=self.member_defs[idx][self.NAME],
                   member_level=self.member_defs[idx][self.LEVEL], idx_member=idx)
            for idx in self.member_defs.keys()
        ])

        self.edit_mode = False
        self.database._flush_cache()
        return self

    def rollback(self) -> Dimension:
        """
        Rollback all changes since 'edit_begin()' was called and ends the edit mode.

        :return: The dimension itself.
        """
        self.from_json(self.recovery_json)
        self.edit_mode = False
        return self

    # endregion

    # region member context
    @property
    def members(self) -> MemberList:
        """
        Returns the list of member in the dimension.
        :return:
        """
        return self._members

    def member(self, member) -> Member:
        if type(member) is int:
            try:
                member_name = self.member_defs[member][1]
                return Member(dimension=self, member_name=member_name,
                              cube=None, idx_dim=-1,
                              idx_member=member,
                              member_level=self.member_defs[self._member_idx_lookup[member_name]][self.LEVEL])
            except (IndexError, ValueError):
                raise KeyError(f"Failed to return Member with index '{member}'. The member does not exist.")

        elif member in self._member_idx_lookup:
            idx_member = self._member_idx_lookup[member]
            return Member(dimension=self, member_name=member,
                          cube=None, idx_dim=-1,
                          idx_member=idx_member,
                          member_level=self.member_defs[self._member_idx_lookup[member]][self.LEVEL])
        raise KeyError(f"Failed to return Member '{member}'. The member does not exist.")

    # region add, remove, rename member_defs
    def add_member(self, member, children=None, description=None, number_format=None) -> Dimension:
        """Adds one or multiple member_defs and (optionally) associated child-member_defs to the dimension.

        :param member: A single string or an iterable of strings containing the member_defs to be added.
        :param children: A single string or an iterable of strings containing the child member_defs to be added.
               If parameter 'member' is an iterable of strings, then children must be an iterable of same size,
               either containing strings (adds a single child) or itself an iterable of string (adds multiple children).
        :param description: A description for the member to be added. If parameter 'member' is an iterable,
               then description will be ignored. For that case, please set descriptions for each member individually.
        :param number_format: A format string for output formatting, e.g. for numbers or percentages.
               Formatting follows the standard Python formatting specification at
               <https://docs.python.org/3/library/string.html#format-specification-mini-language>.
        :return Dimension: Returns the dimension itself.
        """
        if not self.edit_mode:
            raise TinyOlapDimensionEditModeError("Failed to add member. Dimension is not in edit mode.")

        member_list = member
        children_list = children
        multi = False

        if isinstance(member, str):
            if not self.__valid_member_name(member):
                raise KeyError(f"Failed to add member. Invalid member name '{member}'. "
                               f"'\\t', '\\n' and '\\r' characters are not supported.")

            member_list = [member, ]
            children_list = [children]
            multi = True
        elif type(member) is Member:
            member_list = [member.name, ]
            children_list = [children]
            multi = True

        if not children:
            children_list = [None] * len(member_list)

        for m, c in zip(member_list, children_list):
            # add the member
            idx_member = self.__member_add_parent_child(member=m, parent=None,
                                                        description=(None if multi else description))
            if number_format:
                self.member_defs[idx_member][self.FORMAT] = number_format

            if c:
                # add children
                if isinstance(c, str):
                    c = [c]
                # elif not (isinstance(c, Sequence) and not isinstance(c, str)):
                elif not (isinstance(c, Iterable) and not isinstance(c, str)):
                    raise TinyOlapDimensionEditModeError(
                        f"Failed to member '{m}' to dimension '{self._name}'. Unexpected type "
                        f"'{type(c)}' of parameter 'children' found.")
                for child in c:
                    if type(child) is Member:
                        child = child.name
                    if not isinstance(child, str):
                        raise TinyOlapDimensionEditModeError(
                            f"Failed to add child to member '{m}' of dimension '{self._name}. Unexpected type "
                            f"'{type(c)}' of parameter 'children' found.")
                    if not self.__valid_member_name(child):
                        raise KeyError(f"Failed to add member. Invalid member name '{child}'. "
                                       f"'\\t', '\\n' and '\\r' characters are not supported.")
                    self.__member_add_parent_child(member=child, parent=m, weight=1.0)

        return self

    def rename_member(self, member: str, new_name: str, new_description: str = None):
        """Renames a member."""
        if member not in self._member_idx_lookup:
            raise ValueError("Invalid or empty member name.")
        if not new_name:
            raise ValueError("Invalid or empty new member name.")
        if new_name == "*":
            raise ValueError("Invalid member new name. '*' is not a valid member name.")
        if new_name in self.member_defs:
            raise ValueError("New name already exists.")

        idx_member = self._member_idx_lookup[member]
        self.member_defs[idx_member][self.DESC] = (new_description if new_description else member)
        self._member_idx_lookup.pop(member)
        self._member_idx_lookup[new_name] = idx_member

        # adjust subsets
        for subset in self._dict_subsets:
            if member in subset[self.MEMBERS]:
                idx = subset[self.MEMBERS].index(member)
                subset[self.MEMBERS][idx] = new_name

    def remove_member(self, member):
        """
        Removes one or multiple member_defs from a dimension.

        :param member: The member or an iterable of member_defs to be deleted.
        """
        member_list = member
        if isinstance(member, str):
            member_list = [member]

        # Ensure all member_defs exist
        for member in member_list:
            if member not in self._member_idx_lookup:
                raise TinyOlapDimensionEditModeError(f"Failed to remove member(s). "
                                                 f"At least 1 of {len(member_list)} member ('{member}') is not "
                                                 f"a member of dimension {self._name}")

        # remove from directly related member_defs
        for member in member_list:
            idx = self._member_idx_lookup[member]
            children = list(self.member_defs[idx][self.CHILDREN])
            parents = list(self.member_defs[idx][self.PARENTS])

            for child in children:
                if idx in self.member_defs[child][self.PARENTS]:
                    self.member_defs[child][self.PARENTS].remove(idx)
            for parent in parents:
                if idx in self.member_defs[parent][self.CHILDREN]:
                    self.member_defs[parent][self.CHILDREN].remove(idx)

        # remove from all related member_defs
        for all_idx in self._member_idx_lookup.values():
            for member_idx in [self._member_idx_lookup[member] in member_list]:
                if member_idx in self.member_defs[all_idx][self.ALL_PARENTS]:
                    self.member_defs[all_idx][self.ALL_PARENTS].remove(member_idx)
                if member_idx in self.member_defs[all_idx][self.BASE_CHILDREN]:
                    self.member_defs[all_idx][self.BASE_CHILDREN].remove(member_idx)

        # remove the member_defs
        member_idx_to_remove = [self._member_idx_lookup[m] for m in member_list]
        self._member_idx_manager.push(member_idx_to_remove)

        for m in member_list:
            del self._member_idx_lookup[m]
        for idx in member_idx_to_remove:
            if idx in self.member_defs:
                del self.member_defs[idx]

        # adjust subsets
        for subset in self._dict_subsets.values():
            members_to_remove = set(member_list).intersection(set(subset[self.MEMBERS]))
            if members_to_remove:
                for member in members_to_remove:
                    idx = subset[self.MEMBERS].index(member)
                    subset[self.MEMBERS].pop(idx)
                    subset[self.IDX_MEMBERS].pop(idx)

    # endregion

    # region member aliases
    def member_add_alias(self, member: str, alias: str):
        """
        Adds a member alias to the dimension. Aliases enable the access of member_defs
        by alternative names or address (e.g. a technical key, or an abbreviation).

        :param member: Name of the member to add an alias for.
        :param alias: The alias to be set.
        :raises KeyError: Raised if the member does not exist.
        :raises TinyOlapDuplicateKeyError: Raised if the alias is already used by another member.
                Individual aliases can only be assigned to one member.

        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not member a of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        if alias in self.alias_idx_lookup:
            raise TinyOlapDuplicateKeyError(f"Duplicate alias. The alias '{alias}' is already used "
                                        f"by member '{self.member_defs[idx_member][self.NAME]}' of dimension'{self._name}'")
        self.alias_idx_lookup[alias] = idx_member

    def remove_alias(self, alias: str):
        """
        Removes a member alias from the dimension.

        :param alias: The alias to be removed.
        """
        if alias not in self.alias_idx_lookup:
            raise KeyError(f"{alias}' is not alias a of dimension'{self._name}'")
        del self.alias_idx_lookup[alias]

    def member_remove_all_aliases(self, member: str):
        """
        Removes all aliases of a member from the dimension.

        :param member: Name of the member to remove the aliases for.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not member a of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        aliases_to_be_deleted = set([key for key, idx in self.alias_idx_lookup.items() if idx == idx_member])
        for alias in aliases_to_be_deleted:
            del self.alias_idx_lookup[alias]

    def member_has_alias(self, member: str) -> bool:
        """
        Checks if for a given member an alias is defined.

        :param member: Name of the member to be checked.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        return idx_member in set(self.alias_idx_lookup.values())

    def member_aliases_count(self, member: str) -> int:
        """
        Returns the number of aliases defined for a given member.

        :param member: Name of the member to be checked.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to return member alias count. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        return len(set([idx for idx in set(self.alias_idx_lookup.values()) if idx == idx_member]))

    def get_member_by_alias(self, alias: str) -> str:
        """
        Returns the name of a member associated with the given.

        :param alias: Name of the alias to be checked.
        :raises KeyError: Raised if the alias does not exist.
        """
        if alias not in self.alias_idx_lookup:
            raise KeyError(f"Failed to get member by alias. '{alias}' is not a member alias of dimension'{self._name}'")
        idx_member = self.alias_idx_lookup[alias]
        return self.member_defs[idx_member][self.NAME]

    def get_member_by_index(self, index: int) -> str:
        """
        Returns the name of a member associated with the given.

        :param index: Index of the member to be returned.
        :raises KeyError: Raised if the alias does not exist.
        """
        if not index in self.member_defs:
            raise KeyError(f"Failed to get member by index. '{index}' is not a member index of dimension'{self._name}'")
        return self.member_defs[index][self.NAME]

    # endregion

    # region member number_format (for output formatting)
    def member_set_format(self, member: str, format_string: str):
        """
        Set a number_format string for output formatting, especially useful for number formatting.
        Member formatting follows the standard Python formatting specification at
        https://docs.python.org/3/library/string.html#format-specification-mini-language.

        :param member: Name of the member to set the number_format for.
        :param format_string: The number_format string to be used. Member formatting follows the standard
               Python formatting specification at
               https://docs.python.org/3/library/string.html#format-specification-mini-language.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set member number_format. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        self.member_defs[idx_member][self.FORMAT] = format_string

    def member_get_format(self, member: str) -> str:
        """
        Returns the number_format string of a member.

        :param member: Name of the member to return the number_format for.
        :return: Returns the number_format string for the member, or ``None`` if no number_format string is defined.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(
                f"Failed to return member number_format. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        return self.member_defs[idx_member][self.FORMAT]

    def member_remove_format(self, member: str):
        """
        Removes the number_format string of a member.

        :param member: Name of the member to remove the number_format for.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(
                f"Failed to remove member number_format. '{member}' is not a member of dimension'{self._name}'")
        idx_member = self._member_idx_lookup[member]
        self.member_defs[idx_member][self.FORMAT] = None

    # endregion

    # region member information functions
    def member_get_ordinal(self, member: str) -> int:
        """
        Returns the ordinal position of a member with the list of member_defs of the dimension.

        :param member: Name of the member to be checked.
        :return: The ordinal position of the member. If the member does not exits -1 will be returned
        """
        if member in self._member_idx_lookup:
            return list(self._member_idx_lookup.keys()).index(member)
        return -1

    def member_exists(self, member: str) -> bool:
        """
        Check if the member exists in the dimension.

        :param member: Name of the member to be checked.
        :return: ``True`` if the member exists, ``False`` otherwise.
        """
        return member in self._member_idx_lookup

    def member_get_index(self, member: str) -> int:
        """
        Returns the database internal index of a member.

        :param member: Name of the member to be evaluated.
        :return: The internal index of the member.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return self._member_idx_lookup[member]

    def member_get_parents(self, member: str) -> MemberList:
        """
        Returns a list of all parents of a member.
        :param member: Name of the member to be evaluated.
        :return: List of parents.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        parents = []
        for idx in self.member_defs[self._member_idx_lookup[member]][self.PARENTS]:
            parents.append(self.member(self.member_defs[idx][self.NAME]))
        return MemberList(self, tuple(parents))

    def member_get_children(self, member: str) -> MemberList:
        """
        Returns a list of all children of a member.

        :param member: Name of the member to be evaluated.
        :return: List of children.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        children = []
        for idx in self.member_defs[self._member_idx_lookup[member]][self.CHILDREN]:
            children.append(self.member(self.member_defs[idx][self.NAME]))
        return MemberList(self, tuple(children))

    def member_get_leaves(self, member) -> MemberList:
        """
        Returns a list of all leave (base level) member_defs of a member.

        :param member: Name of the member to be evaluated.
        :return: List of leave children/member_defs.
        :raises KeyError: Raised if the member does not exist.
        """
        member = str(member)
        if member not in self._member_idx_lookup:
            raise KeyError(f"A member named '{member}' does not exist in dimension'{self._name}'")

        m = self.member_defs[self._member_idx_lookup[member]]
        if m[self.LEVEL] == 0:
            # already a base member, return that
            return MemberList(self, tuple([self.member(member), ]))
        leaves = []
        for idx in m[self.CHILDREN]:
            if self.member_defs[idx][self.LEVEL] > 0:
                members = self.member_get_leaves(self.member_defs[idx][self.NAME])
                leaves.extend(members)
            else:
                leaves.append(self.member(self.member_defs[idx][self.NAME]))
        return MemberList(self, tuple(leaves))

    def member_get_roots(self, member) -> MemberList:
        """
        Returns a list of all root (top level) member_defs of a member.

        :param member: Name of the member to be evaluated.
        :return: List of root parents/member_defs.
        :raises KeyError: Raised if the member does not exist.
        """
        if str(member) not in self._member_idx_lookup:
            raise KeyError(f"A member named '{member}' does not exist in dimension'{self._name}'")

        m = self.member_defs[self._member_idx_lookup[str(member)]]
        if m[self.ALL_PARENTS]:
            return MemberList(self, tuple(
                [self.member(self.member_defs[x][self.NAME]) for x in m[self.ALL_PARENTS]]))
        else:
            # already a root member, return that
            return MemberList(self, tuple([self.member(member), ]))

    def member_get_level(self, member: str):
        """
        Returns the level of a member within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: 0 for leave level member_defs, values > 0 for aggregated member_defs.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return self.member_defs[self._member_idx_lookup[member]][self.LEVEL]

    def member_is_leave(self, member: str):
        """
        Returns True if the member is a leave-level member (member.level = 0) within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: True if the member is a leave-level member, False otherwise.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return self.member_defs[self._member_idx_lookup[member]][self.LEVEL] == 0

    def member_is_root(self, member: str):
        """
        Returns True if the member is a leave-level member (member.level = 0) within the member hierarchy.

        :param member: Name of the member to be evaluated.
        :return: True if the member is a leave-level member, False otherwise.
        :raises KeyError: Raised if the member does not exist.
        """
        if member not in self._member_idx_lookup:
            raise KeyError(f"{member}' is not a member of dimension'{self._name}'")
        return not self.member_defs[self._member_idx_lookup[member]][self.PARENTS]
    # endregion

    # region member enumeration functions (returning lists of member_defs)
    def get_members(self) -> list[str]:
        """
        Returns a list of all member_defs of the dimension.

        :return: List of all member_defs of the dimension.
        """
        return list(self.member_defs[idx][self.NAME] for idx in self._member_idx_lookup.values())
        # return list(str(key) for key in self._member_idx_lookup.keys())

    def get_members_idx(self) -> list[int]:
        """
        Returns a list of indexes of all member_defs of the dimension.

        :return: List of indexes of all member_defs of the dimension.
        """
        return list(self._member_idx_lookup.values())

    def get_members_by_level(self, level: int) -> list[str]:
        """
        Returns a list of all member_defs of the specific member level. 0 identifies the leave level of the dimension.

        :param level: Level of the member_defs to be returned.
        :return: List of member_defs of the specific member level.
        """
        return [self.member_defs[idx_member][self.NAME]
                for idx_member in self.member_defs
                if self.member_defs[idx_member][self.LEVEL] == level]

    def get_top_level(self) -> int:
        """
        Returns the highest member level over all member_defs of the dimension.

        :return: The highest member level over all member_defs of the dimension.
        """
        return max([self.member_defs[idx_member][self.LEVEL] for idx_member in self.member_defs])

    def get_leaves(self) -> list[str]:
        """
        Returns a list of all leave member_defs (member_defs without children = level equals 0) of the dimension.

        :return: List of leave level member_defs of the dimension.
        """
        members = []
        for idx_member in self.member_defs:
            if self.member_defs[idx_member][self.LEVEL] == 0:
                members.append(self.member_defs[idx_member][self.NAME])
        return  members

    def get_aggregated_members(self) -> list[str]:
        """
        Returns a list of all aggregated member_defs (member_defs with children = level greater 0) of the dimension.

        :return: List of aggregated member_defs of the dimension.
        """
        return [self.member_defs[idx_member][self.NAME]
                for idx_member in self.member_defs
                if self.member_defs[idx_member][self.LEVEL] > 0]

    def get_root_members(self) -> list[str]:
        """
        Returns a list of all root member_defs (member_defs with a parent) of the dimension.

        :return: Returns a list of all root member_defs of the dimension.
        """
        members = []
        for idx_member in self.member_defs:
            if not self.member_defs[idx_member][self.PARENTS]:
                members.append(self.member_defs[idx_member][self.NAME])
        return members

    def get_first_member(self) -> str:
        """
        Returns the first member of the dimension.

        :return: Returns the first member_defs of the dimension.
        """
        for idx_member in self.member_defs:
            return self.member_defs[idx_member][self.NAME]
        return ""

    # endregion

    # region attributes
    def attributes_count(self) -> int:
        """
        Returns the number attributes defined in the dimension.

        :return: Number attributes defined in the dimension.
        """
        return len(self._attributes_dict)

    def set_attribute(self, attribute: str, member: str, value):
        """
        Sets an attribute for a specific member of the dimension.

        :param member: Name of the member to set the attribute for.
        :param attribute: Name of the attribute to be set.
        :param value: Value to be set.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :raises TypeError: Raised when the value if not of the expected type.
        """
        if attribute not in self._attributes_dict:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        expected_type = self._attributes_dict[attribute]
        if not type(value) is expected_type:
            raise TypeError(f"Failed to set attribute value. "
                            f"Type of value is '{str(type(value))}' but '{str(expected_type)}' was expected.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self._name}.")
        idx = self._member_idx_lookup[member]
        self.member_defs[idx][self.ATTRIBUTES][attribute] = value

        if self.attribute_query_caching:
            key = attribute + ":" + str(value)
            if key in self.attribute_cache:
                del self.attribute_cache[key]

    def get_attribute(self, attribute: str, member: str):
        """
        Returns the attribute value for a specific member of the dimension.

        :param attribute: Name of the attribute to be returned.
        :param member: Name of the member to get the attribute for.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        :return: The value of the attribute, or ``None`` if the attribute is not defined for the specific member.
        """
        if attribute not in self._attributes_dict:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self._name}.")
        idx = self._member_idx_lookup[member]
        if attribute not in self.member_defs[idx][self.ATTRIBUTES]:
            return None
        return self.member_defs[idx][self.ATTRIBUTES][attribute]


    def get_attribute_type(self, attribute: str):
        """
        Returns the data type of an attribute.

        :param attribute: Name of the attribute to be returned.
        :raises KeyError: Raised when the attribute name does not exist.
        :return: The type of the attribute.
        """
        if attribute not in self._attributes_dict:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        return self._attributes_dict[attribute]

    def has_attribute(self, attribute: str):
        """
        Checks if a specific attribute is defined for the dimension.

        :param attribute: Name of the attribute to be checked.
        :return: ``True``if the attribute exists. ``False`` otherwise.
        """
        return attribute in self._attributes_dict

    def del_attribute_value(self, attribute: str, member: str):
        """
        Deletes an attribute value for a specific member of the dimension.

        :param attribute: Name of the attribute to be deleted.
        :param member: Name of the member to delete the attribute for.
        :raises KeyError: Raised when either the member or the attribute name does not exist.
        """
        if attribute not in self._attributes_dict:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{attribute}' is not an attribute of dimension {self._name}.")
        if member not in self._member_idx_lookup:
            raise KeyError(f"Failed to set attribute value. "
                           f"'{member}' is not a member of dimension {self._name}.")
        idx = self._member_idx_lookup[member]
        if attribute in self.member_defs[idx][self.ATTRIBUTES]:
            del (self.member_defs[idx][self.ATTRIBUTES][attribute])

    def add_attribute(self, attribute_name: str, value_type: type = object):
        """
        Adds an attribute field to the dimension. Attributes enable to store additional information
        along side of dimension member_defs. Attributes have a value_type which is checked when an attribute
        value is set.

        :param attribute_name: Name of the attribute to be added.
        :param value_type: Type of value expected for the attribute. Default value is ``object`` to allow any data.
        :raises TinyOlapInvalidKeyError: Raised when the name of the attribute is invalid.
        :raises TinyOlapDuplicateKeyError: Raised when the name of the attribute already exists.
        """
        if not is_valid_db_object_name(attribute_name):
            raise TinyOlapInvalidKeyError(f"'{attribute_name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if attribute_name in self._attributes_dict:
            raise TinyOlapDuplicateKeyError(f"Failed to add attribute to dimension. "
                                        f"A dimension attribute named '{attribute_name}' already exists.")
        self._attributes_dict[attribute_name] = value_type

    def rename_attribute(self, attribute_name: str, new_attribute_name: str):
        """
        Renames an attribute of a dimension.

        :param attribute_name: The name of the attribute to be renamed.
        :param new_attribute_name: The new name of the attribute.
        :raises TinyOlapInvalidKeyError: Raised when the new name of the attribute is invalid.
        :raises TinyOlapDuplicateKeyError: Raised when the new name of the attribute already exists.
        """
        if not is_valid_db_object_name(new_attribute_name):
            raise TinyOlapInvalidKeyError(f"Failed to rename dimension attribute. "
                                      f"'{new_attribute_name}' is not a valid dimension attribute name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if attribute_name not in self._attributes_dict:
            raise KeyError(f"Failed to rename dimension attribute. "
                           f"A dimension attribute named '{attribute_name}' does not exist.")

        # add new, remove old attribute values
        for member in self.member_defs.values():
            if attribute_name in member[self.ATTRIBUTES]:
                member[self.ATTRIBUTES][new_attribute_name] = member[self.ATTRIBUTES][attribute_name]
                del (member[self.ATTRIBUTES][attribute_name])

    def remove_attribute(self, attribute_name: str):
        """
        Removes an attribute from the dimension.

        :param attribute_name: Name of the attribute to be removed.
        :raises KeyError: Raises KeyError if the attribute name not exists.

        """
        if attribute_name not in self._attributes_dict:
            raise KeyError(f"Failed to remove attribute from dimension. "
                           f"A dimension attribute named '{attribute_name}' does not exist.")
        # delete all values
        for member in self.member_defs.values():
            if attribute_name in member[self.ATTRIBUTES]:
                del (member[self.ATTRIBUTES][attribute_name])
        del (self._attributes_dict[attribute_name])

    def get_members_by_attribute(self, attribute_name: str, attribute_value) -> list[str]:
        """
        Returns all member_defs having a specific attribute value.

        :param attribute_name: Name of the attribute to be analyzed.
        :param attribute_value: Value of the attribute to used for filtering.
        :return:
        """
        if self.attribute_query_caching:
            key = attribute_name + ":" + str(attribute_value)
            if key in self.attribute_cache:
                return self.attribute_cache[key]

        if attribute_name not in self._attributes_dict:
            raise KeyError(f"Failed to return member_defs by attribute. "
                           f"'{attribute_name}' is not an attribute of dimension {self._name}.")
        members = []
        for idx_member in self.member_defs:
            if attribute_name in self.member_defs[idx_member][self.ATTRIBUTES]:
                if self.member_defs[idx_member][self.ATTRIBUTES][attribute_name] == attribute_value:
                    members.append(self.member_defs[idx_member][self.NAME])
        if self.attribute_query_caching:
            key = attribute_name + ":" + str(attribute_value)
            self.attribute_cache[key] = members
        return members

    # endregion

    # region subsets
    def add_subset(self, subset_name: str, members):
        """
        Adds a new subset to the dimension. A subset is a plain list of member_defs,
        useful for calculation and reporting purposes.

        :param subset_name: Name of the subset to be added.
        :param members: A list (iterable) containing the member to be added to the subset.
        :raises TinyOlapInvalidKeyError: Raised when the name of the subset is invalid.
        :raises TinyOlapDuplicateKeyError: Raised when the name of the subset already exists.
        :raises TypeError: Raised when member_defs list is not of the expected type (list or tuple)
        :raises KeyError: Raised when a member from the member_defs list is not contained in the dimension.
        """
        if not is_valid_db_object_name(subset_name):
            raise TinyOlapInvalidKeyError(f"'{subset_name}' is not a valid dimension subset name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if subset_name in self._dict_subsets:
            raise TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
                                        f"A dimension subset named '{subset_name}' already exists.")

        # validate member_defs list
        if not ((type(members) is list) or (type(members) is tuple)):
            raise TypeError(f"Failed to add member_defs to subset '{subset_name}'. "
                            f"Argument 'member_defs' is not of expected type list or tuple, "
                            f"but of type '{type(subset_name)}'.")
        idx_members = []
        for member in members:
            if member in self._member_idx_lookup:
                idx_members.append(self._member_idx_lookup[member])
            else:
                raise KeyError(f"Failed to add member to subset. "
                               f"'{member}' is not a member of dimension {self._name}.")

        # create and add subset
        self._dict_subsets[subset_name] = {self.IDX: self._subset_idx_manager.pop(),
                                           self.NAME: subset_name,
                                           self.MEMBERS: list(members),
                                           self.IDX_MEMBERS: idx_members}

    def has_subset(self, subset_name: str) -> bool:
        """
        Checks if a specific subset is defined for the dimension.

        :param subset_name: Name of the subset to be checked.
        :return: ``True``if the subset exists. ``False`` otherwise.
        """
        return subset_name in self._dict_subsets

    def subsets_count(self) -> int:
        """
        Returns the number subsets defined in the dimension.

        :return: Number subsets defined in the dimension.
        """
        return len(self._dict_subsets)

    def subset_contains(self, subset_name: str, member_name: str) -> bool:
        """
        Checks if a specific member is contained in a subset of the dimension.

        :param subset_name: Name of the subset to be checked.
        :param member_name: Name of the member to be checked.
        :return: ``True``if the member is contained in the subset. ``False`` otherwise.
        """
        if not subset_name in self._dict_subsets:
            raise KeyError(f"Failed to check member contained in subset. "
                           f"'{subset_name}' is not a subset of dimension {self._name}.")
        return member_name in self._dict_subsets[subset_name][self.MEMBERS]

    def rename_subset(self, subset_name: str, new_subset_name: str):
        """
        Renames a subset of the dimension.

        :param subset_name: Name of the subset to be added.
        :param new_subset_name: New name of the subset.
        :raises TinyOlapInvalidKeyError: Raised when the new name for the subset is invalid.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if not is_valid_db_object_name(new_subset_name):
            raise TinyOlapInvalidKeyError(f"'{new_subset_name}' is not a valid dimension subset name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if not subset_name in self._dict_subsets:
            raise KeyError(f"Failed to rename subset. "
                           f"'{subset_name}' is not a subset of dimension {self._name}.")

        subset = self._dict_subsets[subset_name]
        del self._dict_subsets[subset_name]
        self._dict_subsets[new_subset_name] = subset

    def get_subset(self, subset_name: str) -> tuple[str]:
        """
        Returns the list of member from a subset to the dimension.

        :param subset_name: Name of the subset to be return.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if subset_name in self._dict_subsets:
            return self._dict_subsets[subset_name][self.MEMBERS]

        raise KeyError(f"Failed to return list of subset member. "
                       f"'{subset_name}' is not a subset of dimension {self._name}.")

    def remove_subset(self, subset_name: str):
        """
        Removes a subset from the dimension.

        :param subset_name: Name of the subset to be removed.
        :raises KeyError: Raised when the subset is not contained in the dimension.
        """
        if subset_name in self._dict_subsets:
            self._subset_idx_manager.push(self._dict_subsets[subset_name][self.IDX])
            del (self._dict_subsets[subset_name])
            return

        raise KeyError(f"Failed to remove subset. "
                       f"'{subset_name}' is not a subset of dimension {self._name}.")

    # endregion

    # region serialization
    def to_json(self, beautify: bool = False):
        """
        Returns the json representation of the dimension. Helpful for serialization
        and deserialization of a dimension. The json returned by this function is
        the same as the one contained in the SQLite database storage provider (if available).

        :param beautify: Identifies if the json code should be beautified (multiple rows + indentation).
        :return: A json string representing the dimension.
        """
        data = ['{',
                f'"content": "dimension", ',
                f'"name": "{self._name}", ',
                f'"description": "{self.description}", ',
                f'"count": {self.member_counter}, ',
                f'"member_defs": {json.dumps(self.member_defs)}, ',
                f'"lookup": {json.dumps(self._member_idx_lookup)}, ',
                f'"oldsubsets": {json.dumps(self._dict_subsets)}, ',
                f'"oldattributes": {json.dumps(self._attributes_dict)}, ',
                f'"subsets": {self._subsets.to_json()}, ',
                f'"attributes": {self._attributes.to_json()}',
                '}',
                ]
        json_string = ''.join(data)
        if beautify:
            parsed = json.loads(json_string)
            json_string = json.dumps(parsed, indent=4)
        return json_string

    def from_json(self, json_string: str):
        """
        (Re-)initializes the dimension from a json string.

        .. warning::
            Calling this method for dimensions which are already used by cubes
            will very likely **corrupt your database!** Calling this method is only save
            **before** you create any cube. Handle with care.

        :param json_string: The json string containing the dimension definition.
        :raises TinyOlapFatalError: Raised if an error occurred during the deserialization from json string.
        """
        if not self.edit_mode:
            self.edit()

        try:
            # first, read everything
            dim_def = json.loads(json_string)

            new_name = dim_def["name"]
            new_description = dim_def["description"]
            new_count = dim_def["count"]
            new_members = dim_def["member_defs"]
            new_member_idx_lookup = dim_def["lookup"]
            new_oldattributes = dim_def["oldattributes"]
            new_oldsubsets = dim_def["oldsubsets"]
            new_attributes = dim_def["attributes"]
            new_subsets = dim_def["subsets"]

            # json does not allow non-string address, but we use integer address. Conversion is required.
            new_members = dict_keys_to_int(new_members)

            # second, apply everything (this should not fail)
            self._name = new_name
            self.description = new_description
            self.member_counter = new_count
            self.member_defs = new_members
            self._member_idx_lookup = CaseInsensitiveDict().populate(new_member_idx_lookup)
            self._attributes_dict = new_attributes
            self._dict_subsets = new_subsets
            self._attributes_dict = new_oldattributes
            self._dict_subsets = new_oldsubsets
            self._attributes = Attributes(self).from_dict(new_attributes)
            self._subsets = Subsets(self).from_dict(new_subsets)



            self.commit()
        except Exception as err:
            raise TinyOlapFatalError(f"Failed to load json for dimension '{self._name}'. {str(err)}")

    # endregion

    # region auxiliary function to add, remove or rename member_defs
    @staticmethod
    def __valid_member_name(name):
        return not (("\t" in name) or ("\n" in name) or ("\r" in name))

    def __member_add_parent_child(self, member, parent, weight: float = 1.0, description: str = None) -> int:
        if member in self._member_idx_lookup:
            member_idx = self._member_idx_lookup[member]
            if description:
                self.member_defs[member_idx][self.DESC] = description
            if parent:
                self.__add_parent(member, parent)
        else:
            self.member_counter += 1
            member_idx = self._member_idx_manager.pop()
            self._member_idx_lookup[member] = member_idx
            self.member_defs[member_idx] = {self.IDX: member_idx,
                                            self.NAME: member,
                                            self.DESC: (description if description else member),
                                            self.PARENTS: [],
                                            self.ALL_PARENTS: [],
                                            self.CHILDREN: [],
                                            self.LEVEL: 0,
                                            self.ATTRIBUTES: {},
                                            self.BASE_CHILDREN: [],
                                            self.ALIASES: [],
                                            self.FORMAT: None,
                                            }

            if parent:
                self.__add_parent(member, parent)
        return member_idx

    def __add_parent(self, member: str, parent: str = None):
        member_idx = self._member_idx_lookup[member]
        level = self.member_defs[member_idx][self.LEVEL]
        if parent not in self._member_idx_lookup:
            # create parent member
            self.member_counter += 1
            parent_idx = self.member_counter
            self._member_idx_lookup[parent] = parent_idx
            self.member_defs[parent_idx] = {self.IDX: parent_idx,
                                            self.NAME: parent,
                                            self.DESC: parent,
                                            self.PARENTS: [],
                                            self.ALL_PARENTS: [],
                                            self.CHILDREN: [member_idx],
                                            self.LEVEL: level + 1,
                                            self.ATTRIBUTES: {},
                                            self.BASE_CHILDREN: [],
                                            self.ALIASES: [],
                                            self.FORMAT: None,
                                            }
        else:
            parent_idx = self._member_idx_lookup[parent]
            self.member_defs[parent_idx][self.LEVEL] = level + 1
            if member_idx not in self.member_defs[parent_idx][self.CHILDREN]:
                self.member_defs[parent_idx][self.CHILDREN].append(member_idx)

        # add new parent to member
        if parent_idx not in self.member_defs[member_idx][self.PARENTS]:
            self.member_defs[member_idx][self.PARENTS].append(parent_idx)

        # check for circular references
        if self.__circular_reference_detection(member_idx, member_idx):
            # remove the relationship
            self.member_defs[member_idx][self.PARENTS].remove(parent_idx)
            self.member_defs[parent_idx][self.CHILDREN].remove(member_idx)

            raise TinyOlapDimensionEditModeError(f"Circular reference detected on adding parent <-> child relation "
                                             f"'{self.member_defs[parent_idx][self.NAME]}' <-> "
                                             f"'{self.member_defs[member_idx][self.NAME]}' "
                                             f"to dimension {self._name}. Both member_defs were added, "
                                             f"but the relation was not created.")

        # update all-parents list, only relevant for base level member_defs
        self.__update_all_parents(member_idx, parent_idx)

    def __update_all_parents(self, idx, parent_idx):
        if self.member_defs[idx][self.LEVEL] > 0:
            for child_idx in self.member_defs[idx][self.CHILDREN]:
                self.__update_all_parents(child_idx, parent_idx)
        else:
            if parent_idx not in self.member_defs[idx][self.ALL_PARENTS]:
                self.member_defs[idx][self.ALL_PARENTS].append(parent_idx)

    def __update_member_hierarchies(self):
        for idx in self._member_idx_lookup.values():
            if self.member_defs[idx][self.LEVEL] > 0:
                # update base level children
                self.member_defs[idx][self.BASE_CHILDREN] = self.__get_base_members(idx)
            else:
                self.member_defs[idx][self.ALL_PARENTS] = self.__get_all_parents(idx)

    def __check_circular_reference(self):
        for idx in self._member_idx_lookup.values():
            if self.__circular_reference_detection(idx, idx):
                raise TinyOlapDimensionEditModeError(f"Failed to commit dimension. Circular reference detected "
                                                 f"for member {self.member_defs[idx][self.NAME]}.")

    def __circular_reference_detection(self, start: int, current: int, visited=None):
        if visited is None:
            visited = set()

        if current in visited:
            return True

        visited.add(current)
        for parent in self.member_defs[current][self.PARENTS]:
            if self.__circular_reference_detection(current, parent, visited):
                return True
        visited.remove(current)
        return False

    def __get_all_parents(self, idx) -> list[int]:
        all_parents = []
        for parent in self.member_defs[idx][self.PARENTS]:
            all_parents.append(parent)
            all_parents = all_parents + self.__get_all_parents(parent)
        return all_parents

    def __get_base_members(self, idx) -> list[int]:
        if self.member_defs[idx][self.LEVEL] == 0:
            return [idx]
        else:
            base_members = []
            for child_idx in self.member_defs[idx][self.CHILDREN]:
                if self.member_defs[child_idx][self.LEVEL] == 0:
                    base_members.append(child_idx)
                else:
                    base_members.append(self.__get_base_members(child_idx))
            return base_members
    # endregion
