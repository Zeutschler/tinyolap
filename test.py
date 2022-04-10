from multiprocessing import freeze_support

from tests import test_area
import unittest


# preferred module name would be test_protol as CamelCase convention are used for class name

def main():
    # try to load all testcases from given module, hope your testcases are extending from unittest.TestCase
    suite = unittest.TestLoader().discover("tests", pattern='test_*.py', top_level_dir=None)
    # run all tests with verbosity
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    freeze_support()
    main()
