from unittest import TestCase

from samples.rules import create_rules_database

class TestRules(TestCase):
    """Tests all available samples, except the web_demo (for errors / fatal failure only)."""
    def setUp(self) -> None:
        self.console_output = False  # set to False for unattended testing
        self.db = create_rules_database()

    def test_rule_sales(self):


        pass
