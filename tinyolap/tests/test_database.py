import itertools
from pathlib import Path
from unittest import TestCase

from rules import RuleScope, RuleInjectionStrategy
from tinyolap.decorators import *
from tinyolap.database import Database
from tinyolap.cell_context import CellContext


@rule("sales", ["Profit in %"], scope=RuleScope.ALL_LEVELS,
      injection=RuleInjectionStrategy.FUNCTION_INJECTION, volatile=False)
def rule_profit_in_percent(c: CellContext):
    sales = c["Sales"]
    profit = c["Profit"]
    if sales != 0.0:
        return round((profit / sales) * 100, ndigits=0)
    return None


class TestDatabase(TestCase):

    def setUp(self) -> None:
        self.db_name = "test_database"
        self.db = self.create_database()

    def tearDown(self) -> None:
        # just to be sure...
        if self.db:
            self.db.close()
            self.db.delete()

    def test_Database_create(self):
        """Creates a persistent database with rules (lambda and function level) and some data,
        then the databse will be closed and open again. Then we check if rules are loaded
        properly and cell request deliver the expected values.
        """

        # close the database
        db = self.db
        file_path = db.file_path
        db.close()

        # check if file exists
        self.assertTrue(db._storage_provider.exists(), "Database file exists.")

        # (re)open the database
        db = Database(file_path)
        cube = db.cubes["sales"]
        # check all cells with values
        members = [
            ["2020", "2021", "2022"],
            ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            ["North", "South", "West", "East"],
            ["A", "B", "C"],
            ["Sales", "Cost"]
        ]
        addresses = itertools.product(*members)
        for address in addresses:
            if address[-1] == "Sales":
                self.assertEqual(3.0, cube.get(address))
            else:
                self.assertEqual(2.0, cube.get(address))

            # Ensure the rules have been loaded properly.
            address = address[:-1] + ("Profit",)
            self.assertEqual(1.0, cube.get(address))
            address = address[:-1] + ("Profit in %",)
            self.assertEqual(33.0, cube.get(address))

        # close and clean up
        db.close()
        db.delete()


    def create_database(self) -> Database:
        db = Database(self.db_name, in_memory=False)

        if db.dimension_exists("years"):
            return db

        dim_years = db.add_dimension("years")
        dim_years.edit()
        dim_years.add_member(["2020", "2021", "2022"])
        dim_years.commit()

        dim_months = db.add_dimension("months")
        dim_months.edit()
        dim_months.add_member(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        dim_months.add_member(["Q1", "Q2", "Q3", "Q4"],
                              [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                               ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
        dim_months.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
        dim_months.commit()

        dim_regions = db.add_dimension("regions")
        dim_regions.edit()
        dim_regions.add_member("Total", ("North", "South", "West", "East"))
        dim_regions.commit()

        dim_products = db.add_dimension("products")
        dim_products.edit()
        dim_products.add_member("Total", ["A", "B", "C"])
        dim_products.commit()

        dim_measures = db.add_dimension("measures")
        dim_measures.edit()
        dim_measures.add_member(["Sales", "Cost", "Profit", "Profit in %"])
        dim_measures.commit()

        cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products, dim_measures])
        cube.register_rule(rule_profit_in_percent)
        cube.register_rule(lambda x: x["Sales"] - x["Cost"], "Profit",
                           RuleScope.ALL_LEVELS, RuleInjectionStrategy.FUNCTION_INJECTION)
        cube.register_rule(lambda x: x["jan"] - x["FEB"], "q1",
                           RuleScope.ALL_LEVELS, RuleInjectionStrategy.FUNCTION_INJECTION)

        # disable caching
        cube.caching = False

        # fill all cells with values
        members = [
            ["2020", "2021", "2022"],
            ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            ["North", "South", "West", "East"],
            ["A", "B", "C"],
            ["Sales", "Cost"]
        ]
        addresses = itertools.product(*members)
        for address in addresses:
            if address[-1] == "Sales":
                cube.set(address, 3.0)
            else:
                cube.set(address, 2.0)

        addresses = itertools.product(*members)
        for address in addresses:
            address = address[:-1] + ("Profit",)
            self.assertEqual(1.0, cube.get(address))
            address = address[:-1] + ("Profit in %",)
            self.assertEqual(33.0, cube.get(address))

        db.save()
        return db
