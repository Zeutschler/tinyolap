# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in
# the LICENSE file in the root directory of this source tree.

from __future__ import annotations
import importlib
import warnings
from collections.abc import Iterable, Sequence
import inspect
from abc import ABC, abstractmethod
import fnmatch
import json
from abc import abstractmethod
from enum import Enum
import enum_tools.documentation
from typing import Any

from tinyolap.config import Config
import tinyolap.member as member
import tinyolap.dimension as dimension
import tinyolap.exceptions as exceptions
import tinyolap.utilities.utils as utils
import tinyolap.utilities.case_insensitive_dict as cidict
import tinyolap.utilities.hybrid_dict  as hdict



class Subset(Iterable[member.Member]):
    """Subsets are static or dynamic lists of members from a dimension. They are useful for
    slicing and dicing cube and reporting purposes as well as to implement additional
    static or dynamic aggregations."""
    __slots__ = '_dimension', '_name', '_volatile', '_attributes', '_callable_function', '_members'

    def __init__(self, parent: dimension.Dimension, name: str, volatile: bool, *args):
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
        if not utils.is_valid_db_object_name(name):
            raise exceptions.TinyOlapInvalidKeyError(f"'{name}' is not a valid dimension subset name. "
                                      f"Lower case alphanumeric characters, hyphen and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        self._dimension: dimension.Dimension = parent
        self._name: str = name
        self._volatile: bool = volatile
        self._attributes = None
        self._callable_function = None
        self._members = None

        if (len(args) == 1) and isinstance(args[0], Sequence):
            # static subset defined by a list of members

            # validate Member objects
            for member_arg in args[0]:
                if type(member_arg) is member.Member:
                    if member_arg.dimension is not self._dimension:
                        raise TypeError(f"Failed to initialize static subset '{self._name}' from member list. "
                                        f"At least one member ('{member_arg.name}') is not a member of the parent "
                                        f"dimension '{self._dimension.name} but from "
                                        f"dimension {member_arg.dimension.name}.")

            self._members: hdict.HybridDict[member_arg.Member] = \
                hdict.HybridDict[member.Member](items=[m if type(m) is member.Member else parent.member(str(m)) for m in args[0]],
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

    def __getitem__(self, item):
        self._refresh()
        return self._members[item]


    @property
    def members(self) -> hdict.HybridDict[member.Member]:
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
                    raise exceptions.TinyOlapRuleError(f"Error on calling custom subset function "
                                            f"'{self._callable_function.__name__}'. {str(e)}")

                self._members = hdict.HybridDict[member.Member](
                    items=[m if type(m) is member.Member else self._dimension.member(str(m)) for m in members],
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
                            self._members = hdict.HybridDict[member.Member](items=[], source=self._dimension) # empty subset
                            return
                self._members = hdict.HybridDict[member.Member](items=list(result), source=self._dimension) # empty subset

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

        data["members"] = [str(m) for m in self.members]
        return data

    def from_dict(self, data: dict) -> Subset:
        """
        **FOR INTERNAL USE!** Loads the subset from a dict object,
        normally created by the use of the 'to_dict(...)' function.

        :param data: The dict object to read from.
        """
        try:
            utils.check_content_type_and_version(data["contentType"], data["version"], Config.ContentTypes.SUBSET)

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
                    raise exceptions.TinyOlapSerializationError(f"Failed to re-instantiate function "
                                                     f"'{callable_function}' form module "
                                                     f"'{callable_function_module}'. {str(e)}")

            # restore the attribute query definition
            self._attributes = data["attributeQuery"]

            # finally, restore the saved members that eblogn to the subset.
            self._members = hdict.HybridDict[member.Member](source=self._dimension,
                                               items=[self._dimension.members[m] for m in data["members"]])

        except Exception as e:
            raise exceptions.TinyOlapSerializationError(f"Failed to deserialize '{Config.ContentTypes.ATTRIBUTE}'. "
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
    __slots__ = '_dimension', '_subsets'

    def __init__(self, parent: dimension.Dimension):
        self._dimension: dimension.Dimension = parent
        self._subsets: hdict.HybridDict[Subset] = hdict.HybridDict[Subset](source=parent)

    def __getitem__(self, item) -> Subset:
        """
        Returns a subset by name or index.
        :param item: Name or index of the subset to be returned.
        :return: The requested subset.
        """
        return self._subsets.__getitem__(item)

    def __contains__(self, item):
        return item in self._subsets

    def __len__(self):
        return len(self._subsets)

    def __iter__(self):
        for subset in self._subsets:
            yield subset

    def __delitem__(self, key):
        del self._subsets[key]

    @property
    def dimension(self) -> dimension.Dimension:
        """
        Returns the parent dimension of the subset list.
        """
        return self._dimension

    def clear(self) -> Subsets:
        """
        Removes all subsets from the subset list.
        :return: The subset list itself.
        """
        self._subsets: hdict.HybridDict[Subset] = hdict.HybridDict[Subset](source=self._dimension)
        return self

    def remove(self, subset) -> Subsets:
        """
        Removes a specific subset from the list of subsets.
        :param subset: The subset or the name of the subset to be removed.
        :return: The subset list itself.
        """
        del self._subsets[subset]
        return self

    def add(self, name: str, members) -> Subset:
        """
        Add a static member subset based on a list of members to the dimension.
        :param name: The name of the subset to be created.
        :param members: The list of members to be contained in the subset.
        :return: Returns the added created subset.
        """
        return self.add_static_subset(name, members)

    def add_static_subset(self, name: str, members) -> Subset:
        """
        Add a static member subset based on a list of members to the dimension.
        :param name: The name of the subset to be created.
        :param members: The list of members to be contained in the subset.
        :return: Returns the added created subset.
        """
        if name in self._subsets:
            raise exceptions.TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
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
            raise exceptions.TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
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
            raise exceptions.TinyOlapDuplicateKeyError(f"Failed to add subset to dimension. "
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
                "subsets": [subset.to_dict() for subset in self._subsets]
                }

    def from_dict(self, data: dict) -> Subsets:
        """
        **FOR INTERNAL USE!** Loads the subsets from a dict object,
        normally created by the use of the 'to_dict(...)' function.

        :param data: The dict object to read from.
        """
        self.clear()
        try:
            utils.check_content_type_and_version(data["contentType"], data["version"], Config.ContentTypes.SUBSETS)

            # read all available attributes
            for subset_data in data["subsets"]:
                subset = Subset(self._dimension,  # the 'self' argument indicates deserialization
                                "_", False, self).from_dict(subset_data)
                self._subsets.append(subset)

        except Exception as e:
            raise exceptions.TinyOlapSerializationError(f"Failed to deserialize '{Config.ContentTypes.SUBSETS}'. "
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

