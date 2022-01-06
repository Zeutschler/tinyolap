# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# Purpose: Contains the buisiness logic required for the Enterprise sample database
import math, statistics
import time

from tinyolap.decorators import rule
from tinyolap.rules import RuleScope, RuleInjectionStrategy
from tinyolap.cell import Cell
from tinyolap.database import Database


# region Curreny Conversion Rules
@rule(cube="sales", trigger=["Profit"],
      scope=RuleScope.ALL_LEVELS, injection=RuleInjectionStrategy.MODULE_INJECTION)
def rule_profit(c: Cell):
    return c["Sales"] - c["Cost"]


@rule(cube="sales", trigger=["Profit in %"],
      scope=RuleScope.ALL_LEVELS, injection=RuleInjectionStrategy.MODULE_INJECTION)
def rule_profit_in_percent(c: Cell):
    sales = c["Sales"]
    profit = c["Profit"]
    if sales:
        return profit / sales
    return None
# endregion

# region P&L statement


# endregion
