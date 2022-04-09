from unittest import TestCase

from samples.enterprise import play_enterprise
from samples.tiny import play_tiny
from samples.huge import play_huge
from samples.tiny42 import play_tiny42
from samples.tutor import play_tutor
from samples.planespotter import play_plane_spotter


class Test(TestCase):
    """Tests all available samples, except the web_demo (for errors / fatal failure only)."""
    def setUp(self) -> None:
        self.console_output = False  # set to False for unattended testing

    def test_sample_database_tiny(self):
        play_tiny(console_output=self.console_output)

    # the following test would take 10+ seconds to execute and eats a lot of RAM.
    # def test_sample_database_huge(self):
    #    play_huge(console_output=self.console_output)

    def test_sample_database_planespotter(self):
        play_plane_spotter(console_output=self.console_output)

    def test_sample_database_tutor(self):
        play_tutor(console_output=self.console_output)

    def test_sample_database_tiny42(self):
        play_tiny42(console_output=self.console_output)

    def test_sample_database_finance(self):
        play_enterprise(console_output=self.console_output)
