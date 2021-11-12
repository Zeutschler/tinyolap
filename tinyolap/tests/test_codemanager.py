from unittest import TestCase
from tinyolap.codemanager import *
from tinyolap.decorators import *
from tinyolap.rules import RuleScope, RuleInjectionStrategy


@rule("test", ["member"], scope=RuleScope.ALL_LEVELS, injection=RuleInjectionStrategy.MODULE_INJECTION)
def rule_mock(e):
    return e

class TestCodeFunction(TestCase):
    pass

    def test_codemanager(self):
        cm = CodeManager()
        cf = cm.register_function(rule_mock)
        print(f"function '{cf.name}':")
        print(cf.code)

        cm.build()



