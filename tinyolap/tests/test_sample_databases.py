from unittest import TestCase
import tutor, tiny


class Test(TestCase):

    def test_sample_database_tiny(self):
        """
        Creates and loads the tutor_files sample database from text files.
        The only test criteria is, that the sample does not fail (raise exceptions).
        """
        tiny.play(console_output=False)

    def test_sample_database_tutor(self):
        """
        Creates and loads the tutor_files sample database from text files.
        The only test criteria is, that the sample does not fail (raise exceptions).
        """
        tutor.play(console_output=False)

