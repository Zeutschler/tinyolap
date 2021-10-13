from unittest import TestCase
from tinyolap.samples.tiny import play_tiny
from tinyolap.samples.tutor import play_tutor


class Test(TestCase):

    def test_sample_database_tiny(self):
        """
        Creates and loads the tutor_files sample database from text files.
        The only test criteria is, that the sample does not fail (raise exceptions).
        """
        play_tutor(console_output=False)

    def test_sample_database_tutor(self):
        """
        Creates and loads the tutor_files sample database from text files.
        The only test criteria is, that the sample does not fail (raise exceptions).
        """
        play_tutor(console_output=False)

