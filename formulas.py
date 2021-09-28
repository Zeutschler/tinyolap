# importing the module
import enum
from types import FunctionType
import time
import re
import math


class RulesCompilationError(Exception):
    """Occurs when the validation or compilation of a rule fails."""
    pass


class RulesExecutionError(Exception):
    """Occurs when the execution of a rule fails."""
    pass


class Formulas:
    """represents a set of formulas to be used for cube calculations beyond simple aggregation."""

    class FormulaType(enum.Enum):
        UNIVERSAL = 0
        PUSH_DOWN = 1
        AGGREGATION = 2

    def __init__(self, cube):
        self.cube = cube
        self.formulas = []               # list of registered formulas
        self.triggered_formulas = {}     # list of formulas indexes, access by triggers
        self.triggers = set()            # Set of all yet registered triggers
        self.targets = set()             # set of all yet registered targets
        self.target_formulas = {}        # list of formulas indexes, access by targets

    def add(self, formula: str) -> (bool, str):
        """Adds a new formula to the formula collection. If the formula was successfully added to the Cube,
        then the values <True> and <None> will be return, on failure the value <False> and an error message
        will be returned."""
        # validate formula and generate source code
        success, message, formula_type, formula_function_name, target, detected_triggers, tokens, code, comment \
            = self.__compile_measure_rule(formula)
        if not success:
            return False, message
        if target in self.targets:
            return False, f"Formula compilation failed. A formula definition for target [{target}] already exists."

        # compile the generated formula source code
        try:
            code_object = compile(code, "<float>", "exec")
            func = FunctionType(code_object.co_consts[0], globals(), formula_function_name)
        except (SyntaxError, ValueError) as err:
            return False, f"Formula compilation failed. {str(err)}"

        # Setup a new rule and save it
        rule = {"type": formula_type, "formula": formula, "func": func,
                "target": target, "triggers": detected_triggers, "tokens": tokens,
                "comment": comment}
        idx_new_formula = len(self.formulas)
        self.formulas.append(rule)

        # Register the target
        self.targets.add(target)
        self.target_formulas[target] = idx_new_formula

        # Register triggers
        for trigger in detected_triggers:
            self.triggers.add(trigger)
            if trigger not in self.triggered_formulas:
                self.triggered_formulas[trigger] = [idx_new_formula]
            else:
                if idx_new_formula not in self.triggered_formulas[trigger]:
                    self.triggered_formulas[trigger].append(idx_new_formula)

    def on_set(self, super_level, address, measure, value):
        # Evaluates if any formulas will be triggered by the given measure.
        # If yes all triggered formulas will be executes and the results will be written to the target of the formulas.
        if super_level == 0 and measure in self.triggered_formulas:
            for formula_idx in self.triggered_formulas[measure]:
                if self.formulas[formula_idx]["type"] != Formulas.FormulaType.PUSH_DOWN:
                    continue  # we are interested in push down formulas only

                variables = []
                for trigger in self.formulas[formula_idx]["triggers"]:  # trigger (should) have already the right order
                    if trigger == measure:
                        variables.append(value)
                    else:
                        variables.append(self.cube.get(address, trigger))

                # execute the compiled formula function
                result = self.formulas[formula_idx]["func"](variables)
                # due to inaccuracy of float operations, some rounding is required.
                if result < 1:
                    result = round(result, 10)
                elif result > 100_000.0:
                    result = round(result, 4)
                else:
                    result = round(result, 6)

                # write result to target
                self.cube.set(address, self.formulas[formula_idx]["target"], result)
        return True

    def on_get(self, super_level, address, measure):
        # Evaluates if a formula is defined for the given measure. If yes, the formula will be calculated
        # and the boolean value 'True' and the calculation result will be returned. If not 'False' and 'None'
        # will be returned.
        if type(measure) is list:
            measure = measure[0]
        if measure in self.targets:
            idx_formula = self.target_formulas[measure]
            formula_type = self.formulas[idx_formula]["type"]
            if (super_level == 0) and (formula_type == Formulas.FormulaType.AGGREGATION):
                return False, None # we are interested in aggregation formulas on base level cells

            variables = []
            for trigger in self.formulas[idx_formula]["triggers"]:  # trigger (should) have already the right order
                variables.append(self.cube.get(address, trigger))

            # execute the compiled formula function
            result = self.formulas[idx_formula]["func"](variables)

            # due to inaccuracy of float operations, some rounding is required.
            if result < 1:
                result = round(result, 10)
            elif result > 100_000.0:
                result = round(result, 4)
            else:
                result = round(result, 6)

            return True, result

        return False, None  # no suitable formula

    def __compile_measure_rule(self, formula:str):
        success = True
        message = ""
        comment = ""
        formula_type = Formulas.FormulaType.UNIVERSAL
        name = None
        code = None
        triggers = []
        target = None

        formula = formula.strip()
        # 1. check for prefixes to detect formula type
        if formula.lower().startswith("p:"):
            formula_type = Formulas.FormulaType.PUSH_DOWN
        elif formula.lower().startswith("a:"):
            formula_type = Formulas.FormulaType.AGGREGATION

        # 2. look for first equal sign '=' to split target and formula definition
        pos_equal = formula.find("=")
        if pos_equal == -1:
            return False, f"Invalid formula. Assigment operator '=' missing in formula.",\
                   formula_type, name, target, triggers, code, comment

        # 3. get all measure tokens [ ... ] from formula and validate them
        measure_tokens = re.findall(r"\[.*?\]", formula)
        cube_measures = self.cube.get_measures()
        tokens = []
        pos = 0
        for measure_token in measure_tokens:
            token_info = {"token": measure_token}

            # extract the measure name
            measure: str = measure_token[1:-1].strip()
            if measure.startswith(('"', "'")) and measure.endswith(('"', "'")):
                measure = measure[1:-1].strip()
            if measure not in cube_measures:
                return False, f"Invalid formula. Unknown measure {measure} found in formula. Check spelling, " \
                              f"maybe just a typo. ", formula_type, name, target, triggers, code, comment
            token_info["measure"] = measure

            # evaluate position
            token_info["is_target"] = (pos == 0)
            if pos == 0:
                target = measure # save the target
            start = formula.find(measure_token, pos)
            length = len(measure_token)
            token_info["start"] = start
            token_info["length"] = length
            pos = (start + length)

            # check if the token was already used before
            token_info["ordinal"] = len(tokens)-1
            token_info["is_func_argument"] = True
            for other in [token for token in tokens if token["measure"] == measure]:
                token_info["ordinal"] = other["ordinal"]
                token_info["is_func_argument"] = False
                break

            tokens.append(token_info)

        # 4. get all triggers
        triggers = list([(token["measure"], token["ordinal"]) for token in tokens
                             if (not token["is_target"]) and (token_info["is_func_argument"] == True)])

        triggers.sort(key=lambda tup: tup[1])  # sort by ordinal
        triggers = [t[0] for t in triggers]

        # 5. setup source code
        name = "formula_" + ''.join(e for e in tokens[0]["measure"] if e.isalnum()).lower()  # should be a valid function name
        formula_code = formula[formula.find('=')+1:].strip()
        for token in tokens:
            variable = f"v[{token['ordinal']}]"
            formula_code = formula_code.replace(token["token"], variable)
        code = f"def {name}(v): return {formula_code}"

        return success, message, formula_type, name, target, triggers, tokens, code, comment
