# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

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