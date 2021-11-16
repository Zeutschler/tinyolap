from enum import Enum

from faker import Faker


class TinySampleFactory:
    """
    A Factory to generate TinyOlap sample data models of various kind for various purposes.
    """
    class ModelType(Enum):
        Sales = 1
        Finance = 2
        HR = 3
        All = 4

    class ModelSize(Enum):
        Local = 1
        Small = 2
        Medium = 3
        Large = 4
        VeryLarge = 5

    def __init__(self):
        self.faker = Faker()

    def create(self):
        # todo: Continue implementation of sample factory
        pass