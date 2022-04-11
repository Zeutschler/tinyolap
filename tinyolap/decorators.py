# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import functools
import inspect

from tinyolap.rules import RuleScope, RuleInjectionStrategy


def rule(cube: str, trigger: list[str], scope: RuleScope = RuleScope.ALL_LEVELS,
         injection: RuleInjectionStrategy = RuleInjectionStrategy.NO_INJECTION,
         volatile: bool = False, command=None):
    """
    Decorator for TinyOlap rule functions.

    :param cube: The cube the rule should be assigned to.
    :param trigger: The cell trigger that should trigger the rule. Either a single member name or a list
                    of member names from different dimensions.
    :param scope: The scope of the rule. Please refer the documentation for further details.
    :param injection: THe injection strategy for the rule
    :param volatile: (optional, default = False) Identifies that the rule may or will return changing
                     results on identical input, e.g. if real-time data integration is used.
    :param command: (optional, default = None) Identifies that this rule will only the triggered
                     and executed by an explicit user command or call to the ``execute()``method of
                     a Cell object.
    """

    def decorator_rule(func):
        @functools.wraps(func)
        def wrapper_rule(*args, **kwargs):
            #args = str(inspect.signature(func))
            #args = args[1: len(args) - 1].split(",")
            return func(*args, **kwargs)

        wrapper_rule.cube = cube
        wrapper_rule.trigger = trigger
        wrapper_rule.scope = scope
        wrapper_rule.injection = injection
        wrapper_rule.volatile = volatile
        wrapper_rule.command = command
        return wrapper_rule

    return decorator_rule

