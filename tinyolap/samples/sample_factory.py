from faker import Faker


class TinySampleFactory:
    """
    A Factory to generate TinyOlap sample data models of various kind for various purposes.
    """

    def __init__(self):
        self.faker = Faker()

    def create