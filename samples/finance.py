# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from enum import IntEnum
from faker import Faker


class TinySampleFinanceFactory:
    """
    A Factory to generate TinyOlap sample data models of various kind for various purposes.
    """
    class ModelType(IntEnum):
        Sales = 1
        Finance = 2
        HR = 3
        All = 4

    class ModelSize(IntEnum):
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


def play_finance(console_output = True):
    pass

def main():
    play_finance(True)


if __name__ == "__main__":
    main()
