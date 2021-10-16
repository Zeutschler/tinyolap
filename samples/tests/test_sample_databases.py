from unittest import TestCase
from samples.tiny import play_tiny
from samples.huge import play_huge
from samples.tutor import play_tutor
from samples.planespotter import play_plane_spotter


class Test(TestCase):
    """Tests all available demo data models (for errors / fatal failure only)."""
    def setUp(self) -> None:
        self.console_output = True # set to true for unattended testing

    def test_sample_database_tiny(self):
        play_tiny(console_output=self.console_output)

    def test_sample_database_huge(self):
        play_huge(console_output=self.console_output)

    def test_sample_database_planespotter(self):
        play_plane_spotter(console_output=self.console_output)

    def test_sample_database_tutor(self):
        play_tutor(console_output=self.console_output)

