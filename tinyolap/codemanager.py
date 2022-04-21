# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import inspect
import io
import json
import random
import string
import tokenize
import types

from tinyolap.exceptions import TinyOlapRuleError
from tinyolap.rules import RuleScope, RuleInjectionStrategy


class ModuleCode:
    def __init__(self, module, name: str, code: str, is_custom_module: bool = True):
        self._name = name
        self._is_custom_module: bool = is_custom_module
        self._code: str = code
        self._module = module

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        return self._code

    def __eq__(self, other):
        if not isinstance(other, ModuleCode):
            return False
        return self._code == other.code

    def contains(self, fragment: str) -> bool:
        if self._code.find(fragment) > -1:
            return True

    @property
    def module(self):
        return self._module

    @module.setter
    def module(self, value):
        self._module = value

    @property
    def name(self):
        return self._name

    @property
    def code(self):
        return self._code

    @property
    def is_custom_module(self):
        return self._is_custom_module


class FunctionCode:
    """
    Represents a code fragment for a single (Rule) function.
    """

    def __init__(self, function, name: str, module, code: str, cube: str = None, trigger=None,
                 scope: RuleScope = None, injection: RuleInjectionStrategy = None):
        self._name = name
        self._module: str = module
        self._code: str = code
        self._cube = cube
        self._trigger = trigger
        self._scope: RuleScope = scope
        self._injection: RuleInjectionStrategy = injection
        self._function = function

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        return self._code

    def __eq__(self, other):
        if not isinstance(other, FunctionCode):
            return False
        return self._code == other.code

    @property
    def function(self):
        """The (Python) function object."""
        return self._function

    @function.setter
    def function(self, value):
        """The (Python) function object."""
        self._function = value

    @property
    def name(self) -> str:
        """The name of the function."""
        return self._name

    @property
    def code(self) -> str:
        """The scource code of the function."""
        return self._code

    @property
    def module(self) -> str:
        """
        A ModuleCode object that represents the code module in which the function was defined.
        Only available if the injection strategy is defined for module scope or higher.
        """
        return self._module

    def has_module(self) -> bool:
        """Identifies if the FunctionCode object has an assigned ModuleCode object."""
        return bool(self._module)

    @property
    def cube(self) -> str:
        """The cube the function has been assigned to."""
        return self._cube

    @property
    def trigger(self):
        """The trigger the function"""
        return self._trigger

    @property
    def scope(self) -> RuleScope:
        """The rule scope of the function."""
        return self._scope

    @property
    def injection(self) -> RuleInjectionStrategy:
        """The injection strategy defined for the function.
        If no injection strategy is defined, then the rule function
        will not be initialized when a database will be reloaded.
        """
        return self._injection

    def signature(self) -> str:
        """Returns the signature of the FunctionCode object.
        :return : The signature (a json string) of the FunctionCode object.
        """
        return json.dumps({"cube": self._cube, "trigger": str(self._trigger)})

    @property
    def is_valid(self) -> bool:
        """
        Identifies if the function represents a valid rule. This is the case if the rule takes
        at least one argument and *cube* and a *trigger* are defined. Invalid rule functions will
        not be initialized when a database will be reloaded.
        :return:
        """
        if self._function:
            args = str(inspect.signature(self._function))
            args = args[1: len(args) - 1].split(",")
            return bool(self._cube) and bool(self._trigger) and (len(args) > 0)
        return False


class CodeManager:
    """
    Manages code fragments (from functions or modules) used for TinyOlap rules.
    Mainly serialization, deserialization and loading (instantiation) of code.
    """

    def __init__(self):
        self.functions: dict[str, FunctionCode] = {}
        self.modules: dict[str, ModuleCode] = {}
        self._save_pending: bool = False

    @property
    def pending_changes(self) -> bool:
        """Identifies if the code manager conatins pending changes. Used for database persistence."""
        return self._save_pending

    @pending_changes.setter
    def pending_changes(self, value: bool):
        """Identifies if the code manager conatins pending changes. Used for database persistence."""
        self._save_pending = value

    def clear(self):
        """
        Clears the code manager and all contained code fragments.

        .. note::
            Note: Call this method before you want update your rules, to prohibite "ghost rules".
            The signature of each rule is defined by it's *cube* and the *trigger* assignment,
            not by the name or contents of the rule. Even slight changes might to the signature
            will create a new code fragment, then old code fragments are still active and may
            be handled instead of the new code.
        :return:
        """
        self.functions = {}
        self.modules = {}
        self._save_pending = True

    def get_functions(self, cube: str, scope: RuleScope = None) -> list[FunctionCode]:
        """
        Returns a list of FunctionCode objects matching the given parameters.
        :param cube: The cube name to be filtered.
        :param scope: (optional) the rulescope to be filtered.
        :return: a list of FunctionCode object matching the cube name and rule scope.
        """
        if scope:
            return [f for f in self.functions.values() if f.cube == cube and f.scope == scope]
        else:
            return [f for f in self.functions.values() if f.cube == cube]

    def register_function(self, function, cube: str = None, trigger: list[str] = None,
                          scope: RuleScope = None, injection: RuleInjectionStrategy = None,
                          code: str = None) -> FunctionCode:
        """
        Registers a Python function.
        :param code: (optional) the scoure code of the function
        :param function: The function to be registed.
        :param cube: (optional) the cube the function is assigned to.
        :param trigger: (optional) the trigger the function is assigned to.
        :param scope: (optional) scope of the function.
        :param injection: (optional) injectionstrategy of the function,
        :return: A FunctionCode object representing the function.
        """
        is_valid = True

        is_lambda = repr(function).find("<lambda>") != -1
        if not inspect.isroutine(function):
            raise TypeError(f"Argument 'function' is not a Python function, type id '{type(function)}'.")

        # validate settings from @rule decorator (if available)
        # todo: refactoring required > the following code should be moved to the FunctionCode class.
        if hasattr(function, "cube"):
            cube = function.cube
        if hasattr(function, "trigger"):
            trigger = function.trigger
            if trigger:
                if type(trigger) is str:
                    trigger = [trigger, ]
                elif type(trigger) is tuple:
                    trigger = [trigger, ]
                if not type(trigger) is list:
                    trigger = []
            else:
                trigger = []
        else:
            if type(trigger) is str:  # maybe a lazy user forgot to put the trigger into squared brackets
                trigger = [trigger, ]
            elif type(trigger) is tuple:
                trigger = [trigger, ]
            if not type(trigger) is list:
                trigger = []

        if hasattr(function, "scope"):
            scope = function.scope
        if hasattr(function, "injection"):
            injection = function.injection
        elif not injection:
            injection = RuleInjectionStrategy.NO_INJECTION

        # setup the function code object
        if is_lambda:
            name = self._generate_unique_name("tinyolap_lambda_rule_")
            code = self._lambda_to_function_code(function, name, cube, trigger, scope, injection)
        else:
            name = str(function).split(" ")[1]
            if not code:
                try:
                    code = inspect.getsource(function)
                except Exception as err:
                    code = None
        module = inspect.getmodule(function)
        if module:
            module_name = module.__name__
        else:
            module_name = None
        fc = FunctionCode(function, name=name, module=module_name, code=code, cube=cube,
                          trigger=trigger, scope=scope, injection=injection)

        if injection > RuleInjectionStrategy.FUNCTION_INJECTION:
            # We need to remember (persists) the entire module, so...
            module_code = inspect.getsource(module)
            # setup and register (or override) the module code object
            mc = ModuleCode(module=module, name=module_name, code=module_code)
            self.modules[module_name] = mc

        # register (or override) the function
        self.functions[fc.signature()] = fc

        self._save_pending = True
        return fc

    def _lambda_to_function_code(self, function, name: str, cube: str, trigger: list[str],
                                 scope: RuleScope, injection: RuleInjectionStrategy) -> str:
        """Converts a lambda expression into a function body."""

        # get source and extract the 'lambda' expression by tokenization
        source = " ".join([line.strip().removesuffix("\\").strip()
                           for line in inspect.getsource(function).splitlines()])
        tokens = [token for token in tokenize.generate_tokens(io.StringIO(source).readline)]
        lambda_token = None
        end_of_signature_token = None
        terminal_token = None
        for i in range(len(tokens)):
            if tokens[i].string == "lambda" and tokens[i].type == 1:  # type 1 := NAME
                lambda_token = tokens[i]
                # from here we need beyond the next ':' token
                for j in range(i + 1, len(tokens)):
                    if tokens[j].string == ":" and tokens[j].type == 54:  # type 54 := OP
                        end_of_signature_token = tokens[j]
                        # from here we need go up the 'cube' NAME token followed by the '=' OP token. If defined...
                        for k in range(j + 1, len(tokens)):
                            if tokens[k].string == "cube" and tokens[k].type == 1 and \
                                    tokens[k + 1].string == "=" and tokens[k + 1].type == 54:
                                terminal_token = tokens[k - 1]
                                break

                        # ...not found? Search for other terminals.
                        if not terminal_token:
                            end_of_lambda = self._get_end_of_lambda(source, end_of_signature_token.end[1] + 1)
                            if end_of_lambda > 0:
                                for k in range(j + 1, len(tokens)):
                                    if tokens[k].start[1] > end_of_lambda:
                                        terminal_token = tokens[k - 1]
                                        break
                                if not terminal_token:
                                    terminal_token = tokens[-1]
                        break
                break

        if not lambda_token or not end_of_signature_token or not terminal_token:
            raise TinyOlapRuleError("Unable to extract rule from 'lambda' expression.")

        arguments = source[lambda_token.end[1] + 1: end_of_signature_token.start[1]].strip()
        lambda_source = source[end_of_signature_token.end[1] + 1: terminal_token.start[1]].strip()
        source = lambda_source

        indentation = " " * 4
        code = f'@rule(cube="{cube}", trigger={str(trigger)}, scope={str(scope)}, injection={str(injection)})\n'
        code += f'def {name}({arguments}):\n'
        code += f'{indentation}return {source}\n'
        return code

    @staticmethod
    def _get_end_of_lambda(source: str, start: int) -> int:
        # rough evaluation the end of lambda statement.
        depth = 0
        inquote = False
        indquote = False
        for pos, char in enumerate(source[start:]):
            if char in "([{":
                depth += 1
                continue
            if char in ")]}":
                depth -= 1
                continue
            if depth > 0:
                continue
            if not indquote and char == "'":
                inquote = not inquote
            if not inquote and char == '"':
                indquote = not indquote

            if not inquote and not indquote and char == ",":
                return start + pos

        if depth == 0:
            return len(source) - 1

    def build(self):
        """
        Builds (loads and instantiates) all functions available in the code manager.
        :return:
        """
        # todo: Take care about unloading (reloading) module to not
        #      see: https://stackoverflow.com/questions/437589/how-do-i-unload-reload-a-python-module

        # 1. collect all 'modules' that need to be instantiated (no doublets please)
        modules_code = {}
        # if any(self.modules):
        # some_module = list(self.modules.values())[0].module
        for key, function in [(key, value) for key, value in self.functions.items()
                              if value.injection >= RuleInjectionStrategy.MODULE_INJECTION]:
            modules_code[self.modules[function.module].code] = self.modules[function.module]
        # instantiate the code for all distinct modules
        for module_code in modules_code.values():
            name = module_code.name
            source = module_code.code
            self.modules[module_code.name].module = self._code_to_module(name, source)
        # get reference of 'functions' from newly instantiated modules and assign them to the function code objects.
        for key, function in [(key, value) for key, value in self.functions.items()
                              if value.injection >= RuleInjectionStrategy.MODULE_INJECTION]:
            module = self.modules[function.module].module
            function.function = getattr(module, function.name)

        # 2. collect all 'isolated function' that need to be add to a default menu.
        #    ...those that have injection set to RuleInjectionStrategy.FUNCTION_INJECTION
        isolated_function_keys = [key for key, value in self.functions.items()
                                  if value.injection == RuleInjectionStrategy.FUNCTION_INJECTION]
        if isolated_function_keys:
            # generate 1 Python module containing all isolated rule functions
            module_source = self._default_rule_module_source()
            for key in isolated_function_keys:
                module_source += "\n\n" + self.functions[key].code
            module_source += "\n"

            # instantiate code and assign functions
            module_name = self._generate_unique_name("tinyolap_rules_module_")
            module = self._code_to_module(name=module_name, code=module_source)
            for key in isolated_function_keys:
                self.functions[key]._module = module_name
                function_name = self.functions[key].name
                self.functions[key]._function = getattr(module, function_name)

    def to_json(self) -> str:
        """
        Returns a string in json format containing all registered code fragments.
        :return: Json representing the code fragements contained in the code manager.
        """
        code = {}
        modules = []
        for module in self.modules.values():
            mod = {"name": module.name,
                   "is_custom": module.is_custom_module,
                   "code": module.code}
            modules.append(mod)
        code["modules"] = modules
        functions = []
        for function in self.functions.values():
            mod = {"name": function.name,
                   "function": None,
                   "module": function.module,
                   "cube": function.cube,
                   "trigger": function.trigger,
                   "scope": function.scope,
                   "injection": function.injection,
                   "code": function.code}
            functions.append(mod)
        code["functions"] = functions

        return json.dumps(code, indent=4)

    def from_json(self, data: str, build_code: bool = True) -> CodeManager:
        """
        Inititializes the code manager from code fragements supplied in json format.
        :param data: The json data to read from.
        :param build_code: Flag that defines is the code should be directly build and instantiated.
        """
        self.modules = {}
        self.functions = {}
        if not data:
            return self

        config = json.loads(data)
        for function in config["functions"]:
            self.functions[function["name"]] = FunctionCode(
                function=None,
                name=function["name"],
                module=function["module"],
                cube=function["cube"],
                trigger=function["function"],
                scope=function["scope"],
                injection=function["injection"],
                code=function["code"])
        for module in config["modules"]:
            self.modules[module["name"]] = ModuleCode(
                module=None,
                name=module["name"],
                code=module["code"],
                is_custom_module=module["is_custom"])

        if build_code:
            self.build()

        return self

    @staticmethod
    def _generate_unique_name(prefix: str = "tinolap_", length: int = 8):
        """Generate a somehow unique module name, like this 'tinyolap_gwef65lg'"""
        return prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @staticmethod
    def _code_to_module(name: str, code: str):
        """
        Create a new Python code module instance.
        :param name: name of the code module to instantiate.
        :param code: Source code of the code module (UTF-8).
        :return: A python code modul.
        """
        module = types.ModuleType(name)
        exec(code, module.__dict__)
        return module

    @staticmethod
    def _default_rule_module_source() -> str:
        """
        Returns a default module body (mainly imports) for rules
        that are injected on method level (FUNCTION_INJECTION = 1).
        """
        return '\n'.join([
            "import math, cmath, statistics, decimal, fractions, random, datetime, time, re, json",
            "from tinyolap.decorators import *",
            "from tinyolap.database import *",
            "from tinyolap.dimension import *",
            "from tinyolap.cube import *",
            "from tinyolap.rules import *",
        ])
