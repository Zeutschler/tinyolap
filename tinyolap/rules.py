# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
from enum import Enum, IntEnum, IntFlag
import inspect
import enum_tools.documentation

enum_tools.documentation.INTERACTIVE = True


@enum_tools.documentation.document_enum
class RuleError(Enum):
    """Defines error values raised by rules, useing an Excel-alike error format."""
    DIV0 = "#DIV/0!"  # doc: Devision by zero.
    VALUE = "#VALUE!"  # doc: Invalid argument type, e.g. a number was used instead of an expected string.
    REF = "#REF!"  # doc: Invalid reference to a member, dimension, attribute or cube name.
    ERROR = "#ERR!"  # doc: An unknown or unhandable error occurred.


@enum_tools.documentation.document_enum
class RuleScope(IntEnum):
    """
    Defines the scope of a rule. Meaning, to which level of data the rule should be applied.
    """
    ALL_LEVELS = 1  # doc: (default) Indicates that the rule should be executed for base level and aggregated level cells.
    AGGREGATION_LEVEL = 2  # doc: Indicates that the rule should be executed for aggregated level cells only.
    BASE_LEVEL = 3  # doc: Indicates that the rule should be executed for base level cells only.
    ROLL_UP = 4  # doc: Indicates that the rule should replace the base level cell value from the database by the results of the rule. This can dramatically slow down aggregation speed. Requires a special trigger to be set.
    ON_ENTRY = 5  # doc: Indicates that these rules should be executed when cell values are set or changed. This is useful for time consuming calculations which may be *too expensive* to run at idx_address time.
    COMMAND = 6  # doc: Indicates that these rules need to be invoked by a command. Requires the decorator parameter 'command to be specified.

    def __eq__(self, other):
        return self.value == int(other)

    def __ne__(self, other):
        return self.value != other.value

    def __hash__(self):
        return hash(self.value)


@enum_tools.documentation.document_enum
class RuleInjectionStrategy(IntEnum):
    """
    Defines the code injection strategy for individual rules.

    By default, TinyOlap rules reside and will be executed from with your custom code.
    This is preferable for a lot of situations, e.g. for development and debugging,
    or when your business logic require resources that can or should not become a part
    of a TinyOlap database, like calling other systems or systems. When a TinyOlap
    database is running in in-memory mode this is anyhow the only available option
    to provide business logic to a TinyOlap database.

    However, when you intend to hand over a TinyOlap database to someone else, or if
    you want to host it as a generic webservice, then your business logic ideally
    goes with the database.

    To enable this TinyOlap can automatically inject your rule source code into the
    database and persist it with the database. The next time the database will be opened,
    your code will be automatically instantiated and run from within the TinyOlap engine
    itself. You can at anytime override / replace these injected rules with your own
    code by calling  the ``add_rule(...)`` method provide by the *cube* class.

    There are 4 different strategies available how to inject rules into a TinyOlap
    database. Depending on your use case, you should try to use the most restrictive
    strategy possible, as explained below in the documentation of the different
    RuleInjectionStrategy enum values.

    Please be aware that code injection does work on actual code level, not on file level.
    If you have created dynamic code, the code should be properly extracted by TinyOlap.
    """

    NO_INJECTION = 0  # doc: (default) Indicates that the rule should not be injected into the database.
    FUNCTION_INJECTION = 1  # doc: Indicates that **only** the rule function itself will be injected into the database. All surrounding code of the module or project where the rule function is defined, will be ignored. This requires your rule function to be **autonomous**. Meaning, without any dependencies to functions or classes from within your code. By default, TinyOlap will only reference the following built-in Python modules using the ``from [module name] import *`` trigger, when running your code: math, cmath, statistics, decimal, fractions, random, datetime, time, re, json. ``FUNCTION_INJECTION`` should be the preferred strategy for simple business logic that acts upon the data from a TinyOlap database only.
    MODULE_INJECTION = 2  # doc: Indicates that the **entire** module in which the rule function is defined will be injected doc: into the database. Code from other modules of your project will be ignored. If your rules are spread or multiple modules, all these modules will be injected. This requires that all modules and Python packages referenced from within your module must also be installed on the target system. TinyOlap will raise an appropriate error if the instantiation of your code module in the target environment will fail. ``MODULE_INJECTION`` should be the preferred strategy for more complex business logic or business logic that requires certain initialization (e.g. read exchange rates from a service)
    PROJECT_INJECTION = 3  # doc: **NOT YET SUPPORTED** Indicates that the **entire** project in which the rule function is defined will be injected into the database. This

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __hash__(self):
        return hash(self.value)


class Rule:
    """
    Represents a rule, defining custom calculations or business logic to be assigned to a cube.
    """

    def __init__(self, function, name: str, cube: str, trigger: list[str], idx_trigger_pattern: list[tuple[int, int]],
                 scope: RuleScope, injection: RuleInjectionStrategy, code: str = None):
        self.function = function
        self.cube: str = cube
        self.name: str = name
        self.trigger: list[str] = trigger
        self.idx_trigger_pattern = idx_trigger_pattern
        self.scope: RuleScope = scope
        self.injection: RuleInjectionStrategy = injection
        self.code: str = code
        self.signature: str = self.cube + str(idx_trigger_pattern)


class Rules:
    """Represemts a list of rules. Rules define custom calculations or business logic to be assigned to a cube.

    Rules consist two main components:

    * A trigger or trigger, defining the context for which the rule should be executed

    * A scope, defining to which level of data the rule should be applied.
      Either for base level cells, aggregated cells, all cells or on write back of values.

    * A function, defining the custom calculation or business logic. This can be any Python method or function.

    .. attention::

        Rules functions have to be implemented as a simple Python function with just one single parameter and
        a return value. The single parameter should be called 'c' and will contain an TinyOlap Cell, representing
        the current cell context the rule should be calculated for.

        What happens in a rule function, is up totally to the programmer. The value returned by rules function
        can either be a certain value (most often a numerical number, but can be anything) or one of the following
        constants which are directly available from within a cursor object.

        * **NONE** - Indicates that rules function was not able return a proper result (why ever).

        * **CONTINUE** - Indicates that either subsequent rules should continue and do the calculation work
           or that the cell value, either from a base-level or an aggregated cell, form the underlying cube should
           be used.

        * **ERROR** - Indicates that the rules functions run into an error. Such errors will be pushed up to initially
          calling cell request.

        Sample of a proper rule:

        .. code:: python

            def rule_average_price(c : tinyolap.context):
                quantity = c["quantity"]
                sales = c["sales"]
                # ensure both values exist or are of the expected type (cell values can be anything)
                if quantity is float and sales is float:
                    if quantity != 0.0:
                        return sales / quantity
                    return "n.a."  # the developer decided to return some text, what is totally fine.
                return c.CONTINUE
    """

    def __init__(self, cube: str):
        # new implementation
        self.rules: dict[RuleScope, list[Rule]] = {}
        self.patterns: dict[RuleScope, list[list[tuple[int, int]]]] = {}
        self._rules_count: int = 0

        # old implementation
        self.any: bool = False
        self.cube = cube
        self.functions = []
        self.function_names = []
        self.function_scopes = []
        self.function_injections = []
        self.source = []
        self.pattern = []
        self.pattern_idx = []

    def add(self, rule: Rule):
        """
        Adds a new rule to the list of rules. If a rule with the same trigger pattern
        already exists, then the existing rule will be replaceed by the new rule.
        :param rule: The Rule to be added.
        """
        scope = rule.scope
        idx_existing = -1
        if scope in self.rules:
            # Note: sorting matters, as we don't know the sequence in which users define rules !!!
            rule.idx_trigger_pattern.sort()
            for idx, existing_rule in enumerate(self.rules[scope]):
                # check if trigger pattern are identical
                if rule.idx_trigger_pattern == existing_rule.idx_trigger_pattern:
                    # replace existing rule with new rule.
                    idx_existing = idx
                    break
            if idx_existing >= 0:
                # replace rule (the trigger pattern is the same)
                self.rules[scope][idx_existing] = rule
            else:
                # add new rule
                self.rules[scope].append(rule)
                self.patterns[scope].append(rule.idx_trigger_pattern)
        else:
            # add first rule and pattern for this scope
            self.rules[scope] = [rule]
            self.patterns[scope] = [rule.idx_trigger_pattern]

        # update number of rules
        self._rules_count = sum([len(rules) for rules in self.rules.values()])

    def match(self, scope: RuleScope, idx_address: list[tuple[int, int]]) -> (bool, object):
        """
        Returns the first trigger match, if any, for a given cell address.

        :param scope: The rule scope for which a matching rule is requested.
        :param idx_address: The cell address (in index int format) to be evaluated.
        :return: Returns a tuple (True, *function*) if at least one trigger matches,
            *function* is the actual rules function to call, or (False, None) if none
            of the patterns matches the given cell idx_address.

        """
        patterns = self.patterns.get(scope)
        if patterns:
            for idx, function_pattern in enumerate(patterns):  # e.g. [(0,3),(3,2)] >> dim0 = member3, dim3 = member2
                for dim_pattern in function_pattern:  # e.g. (0,3) >> dim0 = member3
                    if idx_address[dim_pattern[0]] != dim_pattern[1]:
                        break
                else:
                    return True, self.rules[scope][idx].function  # this statement will be executed only,
                    # if the inner loop did NOT break

        return False, None

    def __bool__(self):
        return self.functions is True

    def __len__(self):
        return self._rules_count
        # return len(self.functions)

    def register(self, function, cube: str, function_name: str,
                 pattern: list[str], idx_pattern: list[tuple[int, int]],
                 scope: RuleScope, injection: RuleInjectionStrategy, code: str = None):
        """
        Registers a rules function (a Python method or function).

        :param cube: The cube the rule should be registered for.
        :param injection: The injection strategy defined for the rule.
        :param code: (optional) the source code of the rule.
        :param scope: The scope of the rule function.
        :param function_name: Name of the rule function.
        :param function: The Python rule function to execute.
        :param pattern: The cell trigger to trigger the rule function.
        :param idx_pattern: The cell index trigger to trigger the rule function.
        """
        self.functions.append(function)
        self.function_names.append(function_name)
        self.function_scopes.append(scope)
        self.function_injections.append(injection)
        self.pattern.append(pattern)
        if code:
            self.source.append(code)
        else:
            self.source.append(self._get_source(function))
        self.pattern_idx.append(idx_pattern)
        self.any = True

    # def _get_source_code(self, function):
    #     source = inspect.getsource(function)
    #     module = inspect.getmodule(function)
    #     module_source = inspect.getsource(module)
    #     sourcefile = inspect.getsourcefile(function)
    #     print(f"Rule from module {module} and file '{sourcefile}'.")
    #     print(module_source)
    #
    #     return source

    @staticmethod
    def _get_source(function):
        try:
            lines = inspect.getsource(function)
        except Exception as err:
            lines = None
        return lines

    def first_match(self, idx_address) -> (bool, object):
        """
        Returns the first trigger match, if any, for a given cell address.

        :param idx_address: The cell address in index number_format.
        :return: Returns a tuple (True, *function*) if at least one trigger matches,
            *function* is the actual rules function to call, or (False, None) if none
            of the patterns matches the given cell idx_address.

        """
        for idx, function_pattern in enumerate(
                self.pattern_idx):  # e.g. [(0,3),(3,2)] >> dim0 = member3, dim3 = member2
            for dim_pattern in function_pattern:  # e.g. (0,3) >> dim0 = member3
                if idx_address[dim_pattern[0]] != dim_pattern[1]:
                    break
            else:
                return True, self.functions[idx]  # this will be executed only if the inner loop did NOT break
        return False, None
