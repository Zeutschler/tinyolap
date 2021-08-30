from unittest import TestCase
from paceline import paceline
import inspect


class Test(TestCase):
    EXPECTED_RESULT: float = 990000

    @staticmethod
    def some_static_slow_method(loops: int = 100) -> float:
        total: float = 0
        for x in range(0, loops):
            for y in range(0, loops):
                total += x + y
        return total

    @staticmethod
    def some_static_fast_method() -> float:
        return Test.EXPECTED_RESULT

    def some_instance_slow_method(self, loops: int = 100) -> float:
        total: float = 0
        for x in range(0, loops):
            for y in range(0, loops):
                total += x + y
        return total

    def some_instance_fast_method(self) -> float:
        return Test.EXPECTED_RESULT


    def test_default_parameters(self):
        print(f"\n############## OUTPUT FROM TEST {inspect.currentframe().f_code.co_name}")
        self.assertTrue(self.execute(Test.EXPECTED_RESULT), True)

    def test_all_options_on(self):
        print(f"\n############## OUTPUT FROM TEST {inspect.currentframe().f_code.co_name}")
        self.assertTrue(self.execute(Test.EXPECTED_RESULT, iterations=100, progressbar=True, statistics=True,
                                     boxplot=True, histogram=True), True)

    def test_different_iterations(self):
        print(f"\n############## OUTPUT FROM TEST {inspect.currentframe().f_code.co_name}")
        for iterations in [-1, 0, 1, 2, 10, 100]:
            self.assertTrue(self.execute(Test.EXPECTED_RESULT, iterations=100, progressbar=True, statistics=True,
                                         boxplot=True, histogram=True), True)

    def test_suppress_output(self):
        print(f"\n############## OUTPUT FROM TEST {inspect.currentframe().f_code.co_name}")
        self.some_instance_slow_method = paceline(self.some_instance_slow_method,
                                                  suppress_output=True, return_metrics=True)
        result, metrics = self.some_instance_slow_method()
        self.assertTrue(result == Test.EXPECTED_RESULT, True)
        self.assertTrue(type(metrics) is dict, True)
        self.some_instance_slow_method = self.some_instance_slow_method.__wrapped__

    def test_skip(self):
        print(f"\n############## OUTPUT FROM TEST {inspect.currentframe().f_code.co_name}")
        self.some_instance_slow_method = paceline(self.some_instance_slow_method, skip=True)
        self.assertEqual(self.some_instance_slow_method(), Test.EXPECTED_RESULT)
        self.some_instance_slow_method = self.some_instance_slow_method.__wrapped__

    def execute(self, expected_result, iterations: int = 1, skip: bool = False, progressbar: bool = True,
                statistics: bool = False, boxplot: bool = False, histogram: bool = False,
                return_metrics: bool = False, suppress_output: bool = False):
        # Executes tests over different functions with given parameter sets.
        self.some_instance_slow_method = paceline(self.some_instance_slow_method,
                                                  iterations=iterations, skip=skip, progressbar=progressbar,
                                                  statistics=statistics, boxplot=boxplot, histogram=histogram,
                                                  return_metrics=return_metrics, suppress_output=suppress_output)
        self.some_instance_fast_method = paceline(self.some_instance_fast_method,
                                                  iterations=iterations, skip=skip, progressbar=progressbar,
                                                  statistics=statistics, boxplot=boxplot, histogram=histogram,
                                                  return_metrics=return_metrics, suppress_output=suppress_output)
        self.some_static_slow_method = paceline(self.some_static_slow_method,
                                                iterations=iterations, skip=skip, progressbar=progressbar,
                                                statistics=statistics, boxplot=boxplot, histogram=histogram,
                                                return_metrics=return_metrics, suppress_output=suppress_output)
        self.some_static_fast_method = paceline(self.some_static_fast_method,
                                                iterations=iterations, skip=skip, progressbar=progressbar,
                                                statistics=statistics, boxplot=boxplot, histogram=histogram,
                                                return_metrics=return_metrics, suppress_output=suppress_output)

        # testing
        self.assertEqual(self.some_instance_slow_method(), expected_result)
        self.assertEqual(self.some_instance_fast_method(), expected_result)
        self.assertEqual(self.some_static_slow_method(), expected_result)
        self.assertEqual(self.some_static_fast_method(), expected_result)

        # unwrap methods
        self.some_instance_slow_method = self.some_instance_slow_method.__wrapped__
        self.some_instance_fast_method = self.some_instance_fast_method.__wrapped__
        self.some_static_slow_method = self.some_static_slow_method.__wrapped__
        self.some_static_fast_method = self.some_static_fast_method.__wrapped__

        return True
