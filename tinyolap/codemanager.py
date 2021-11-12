import inspect
import types
import json
from enum import IntEnum

import tinyolap.rule_module_template
from tinyolap.rules import RuleScope, RuleInjectionStrategy
from tinyolap.rule_module_template import tinyolap_info

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
            args = args[1: len(args) -1].split(",")
            return bool(self._cube) and bool( self._trigger) and (len(args) > 0)
        return False


class CodeManager:

    def __init__(self):
        self._functions: dict[str, FunctionCode] = {}
        self._modules: dict[str, ModuleCode] = {}

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
        self._functions = {}
        self._modules = {}

    def register_function(self, function, cube: str = None, trigger: list[str] = None,
                          scope: RuleScope = None, injection: RuleInjectionStrategy = None) -> FunctionCode:
        """
        Registers a function.
        :param function: The function to be registed.
        :param cube: (optional) the cube the function is assigned to.
        :param trigger: (optional) the trigger the function is assigned to.
        :param scope: (optional) scope of the function.
        :param injection: (optional) injectionstrategy of the function,
        :return: A FunctionCode object representing the function.
        """
        is_valid = True

        offset = 0
        if not inspect.isroutine(function):
            if callable(function) and function.__name__ == "<lambda>":
                offset = 1
            else:
                raise TypeError(f"Argument 'function' is not a Python function, type id '{type(function)}'.")

        # validate settings from @rule decorator (if available)
        # todo: refactoring required > the following code should be moved to the FunctionCode class.
        if hasattr(function, "cube"):
            cube = function.cube
        if hasattr(function, "trigger"):
            trigger = function.pattern
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
        name = str(function).split(" ")[1 + offset]
        module = inspect.getmodule(function)
        module_name = module.__name__
        code = inspect.getsource(function)
        fc = FunctionCode(function, name=name, module= module_name, code=code, cube=cube,
                          trigger=trigger, scope=scope, injection=injection)

        if injection > RuleInjectionStrategy.METHOD_INJECTION:
            # We need to remember (persists) the entire module, so...
            module_code = inspect.getsource(module)
            # setup and register (or override) the module code object
            mc = ModuleCode(module=module, name=module_name, code=module_code)
            self._modules[module_name] = mc

        # register (or override) the function
        self._functions[fc.signature()] = fc
        return fc

    def build(self):
        """
        Builds or rebuilds (compiles and instantiates) the all functions available
        in the code manager.
        :return:
        """
        # collect all modules that need to be instantiated (no doublets please)
        modules_code = {}
        some_module = list(self._modules.values())[0].module
        for key, fc in [(key, value) for key, value in self._functions.items()
                        if value.injection >= RuleInjectionStrategy.MODULE_INJECTION]:
            modules_code[self._modules[fc.module].code] = self._modules[fc.module]
        # instantiate the code for all distinct modules
        for module_code in modules_code.values():
            self._modules[module_code.name].module = self._code_to_module("tiny" + module_code.name, module_code.code)
        # get reference of functions from instatiated modules and assign them to the function code objects.
        for key, fc in [(key, value) for key, value in self._functions.items()
                        if value.injection >= RuleInjectionStrategy.MODULE_INJECTION]:
            module = self._modules[fc.module].module
            module = some_module
            code = inspect.getsource(module)
            print(module.__dict__)
            fc.function = getattr(module, fc.name)

            # Lets try to call the function
            result = fc.function("Hello World!")
            print(f"We expect 'Hello World!' and got this := '{result}'")


    def _code_to_module(self, name: str,  code: str):
        # create new module
        module = types.ModuleType(name)
        # populate the module with the code
        exec(code, module.__dict__)
        return module

    def _default_module_code(self):
        # Returns a default module body for rules that are injected on method level (METHOD_INJECTION = 1).
        module = inspect.getmodule(tinyolap.rule_module_template.tinyolap_info)
        module_code = inspect.getsource(module)
        return module_code

