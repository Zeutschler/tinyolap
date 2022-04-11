from unittest import TestCase
from tinyolap.codemanager import *
from tinyolap.decorators import *
from tinyolap.rules import RuleScope, RuleInjectionStrategy


@rule("cube", ["member"], scope=RuleScope.ALL_LEVELS, injection=RuleInjectionStrategy.MODULE_INJECTION)
def rule_with_module_injection(e):
    return e


@rule("cube", ["other_member"], scope=RuleScope.ALL_LEVELS, injection=RuleInjectionStrategy.FUNCTION_INJECTION)
def rule_with_function_injection(e, some_optional_parameter: str = "from", another_optional_parameter: str = "function injection."):
    return e + f" {some_optional_parameter} {another_optional_parameter}!"


class TestCodeFunction(TestCase):
    pass

    def setUp(self) -> None:
        self.json = ""

    def test_codemanager(self, console_output:bool = False):

        expected = []
        returned = []
        manager = CodeManager()

        # case 1 - functions from modules
        function_module = manager.register_function(rule_with_module_injection)
        expected.append(function_module.function('Hello World'))

        # case 2 - plain functions (without any surrounding code)
        function_function = manager.register_function(rule_with_function_injection)
        expected.append(function_function.function('Hello World'))

        # case 3 - lambda expression (...igitt, igitt)
        lambda_function1 = manager.register_function(lambda x: x + " from lambda!",
                                                    cube="cube", trigger=["and_another_member"],
                                                    scope=RuleScope.ALL_LEVELS,
                                                    injection=RuleInjectionStrategy.FUNCTION_INJECTION)
        expected.append(lambda_function1.function('Hello World'))

        # case 4 - multiline lambda exression, containing '\' line breaks (...igitt, igitt)
        lambda_function2 = manager.register_function(lambda x:\
                                                    x + \
                                                    " from multiline lambda!",
                                                    cube="cube", trigger=["and_again_another_member"],
                                                    scope=RuleScope.ALL_LEVELS,
                                                    injection=RuleInjectionStrategy.FUNCTION_INJECTION)
        expected.append(lambda_function2.function('Hello World'))

        # convert code to json
        self.json = manager.to_json()
        if console_output:
            print(self.json)

        # rebuild code in a new code manager instance
        another_manager = CodeManager().from_json(self.json)
        # execute all functions
        for function in another_manager.functions.values():
            returned.append(function.function('Hello World'))
            if console_output:
                print(f"Rebuild function call '{function.name}('Hello World') returned: {function.function('Hello World')}")

        # compare results
        for exp, ret in zip(expected, returned):
            self.assertEqual(exp, ret)



