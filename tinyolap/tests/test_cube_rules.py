import itertools
from random import randrange, random, uniform
from unittest import TestCase

from cell import Cell
from database import Database
from decorators import rule
from rules import RuleScope


class TestCubeRules(TestCase):

    def setUp(self) -> None:
        self.db, self.cube_sales, self.cube_exrates = self.create_database()

    def test_all_level_rules(self):
        pass

    def test_aggregation_level_rules(self):
        pass

    def test_base_level_rules(self):
        pass

    def test_roll_up_rules(self):
        pass

    def test_push_down_rules(self):
        pass

    # region Rules Functions
    @rule("sales", ["var"], RuleScope.ALL_LEVELS)
    def calc_var(self, c: Cell):
        return c["actual"] - c["plan"]

    # endregion

    def create_database(self):
        db = Database("sales", in_memory=True)

        dim_years = db.add_dimension("years")
        dim_years.edit()
        dim_years.add_member(["2020", "2021", "2022", "2023"])
        dim_years.commit()

        dim_currency = db.add_dimension("products")
        dim_currency.edit()
        dim_currency.add_member(["EUR", "USD"])
        dim_currency.commit()

        dim_months = db.add_dimension("months")
        dim_months.edit()
        dim_months.add_member(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        dim_months.add_member(["Q1", "Q2", "Q3", "Q4"],
                              [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                               ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
        dim_months.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
        dim_months.commit()

        dim_products = db.add_dimension("products")
        dim_products.edit()
        dim_products.add_member("Total", ["A", "B", "C"])
        dim_products.commit()

        dim_measures = db.add_dimension("measures")
        dim_measures.edit()
        dim_measures.add_member(["Quantity", "Price", "Sales", "Cost", "Profit", "Profit%"])
        dim_measures.commit()

        # ***********************************
        # Sales Cube, filled with random data
        cube_sales = db.add_cube("sales", [dim_currency, dim_years, dim_months, dim_products, dim_measures])
        # set quantities
        addresses = itertools.product(["EUR"],
                                      cube_sales.get_dimension_by_index(1).get_leave_members(),
                                      cube_sales.get_dimension_by_index(2).get_leave_members(),
                                      cube_sales.get_dimension_by_index(3).get_leave_members(),
                                      ["Quantity"])
        for address in addresses:
            cube_sales.set(address, round(uniform(10.0, 1000.0), 0))
        # set prices
        addresses = itertools.product(["EUR"],
                                      cube_sales.get_dimension_by_index(1).get_leave_members(),
                                      cube_sales.get_dimension_by_index(2).get_leave_members(),
                                      cube_sales.get_dimension_by_index(3).get_leave_members(),
                                      ["Quantity"])
        for address in addresses:
            cube_sales.set(address, round(uniform(4.0, 10.0), 2))
        # set cost
        addresses = itertools.product(["EUR"],
                                      cube_sales.get_dimension_by_index(1).get_leave_members(),
                                      cube_sales.get_dimension_by_index(2).get_leave_members(),
                                      cube_sales.get_dimension_by_index(3).get_leave_members(),
                                      ["Cost"])
        for address in addresses:
            cube_sales.set(address, round(uniform(100.0, 1000.0), 2))

        # ********************************************
        # Exchange Rates Cube, filled with random data
        dim_exrate = db.add_dimension("exrate")
        dim_exrate.edit()
        dim_exrate.add_member("exrate")
        dim_exrate.commit()
        cube_exrates = db.add_cube("exrates", [dim_years, dim_months, dim_exrate])
        addresses = itertools.product(cube_exrates.get_dimension_by_index(0).get_leave_members(),
                                      cube_exrates.get_dimension_by_index(1).get_leave_members(),
                                      cube_exrates.get_dimension_by_index(2).get_leave_members())
        for address in addresses:
            cube_exrates.set(address, round(uniform(0.8, 1.2), 4))


        return db, cube_sales, cube_exrates

