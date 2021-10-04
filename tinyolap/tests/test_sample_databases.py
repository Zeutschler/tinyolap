from unittest import TestCase
import tutor


class Test(TestCase):

    def test_sample_database_turor(self):
        """
        Creates and loads the tutor sample database from text files.
        """
        tutor.play(console_output=False)
