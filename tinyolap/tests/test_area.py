import itertools
from random import randrange
from unittest import TestCase
from database import Database


class TestArea(TestCase):

    def setUp(self) -> None:
        self.db, self.cube = self.create_database()

    def test_area_creation(self):

        cube = self.cube
        self.fill_all_cells(cube, 1.0)

        # all should be valid data area definitions
        area = cube.area("2021")
        area = cube.area("2021", "months:Jan", "3:A")
        area = cube.area(["2021", "2022"], "months:Jan", "3:A")
        area = cube.area(["2021", "2022"], "months:Jan", ("A", "C"))
        area = cube.area(["2021", "2022"], "months:Jan", ("products:Total",))

    def test_area_clear(self):

        cube = self.cube
        self.fill_all_cells(cube, 1.0)

        # read from aggregated cells
        address = ("2020", "Q1", "Total", "Total", "Sales")
        value_before = cube.get(address)

        # all valid area definitions
        cube.area("2021").clear()

        value_after = cube.get(address)
        self.assertEqual(0.0, value_after)

    def test_area_math(self):

        cube = self.cube
        self.fill_all_cells(cube, 1.0)

        # multiply
        address = ("2021", "Jan", "North", "A", "Sales")
        value_before = cube.get(address)

        cube.area("2021").multiply(2.0)

        value_after = cube.get(address)
        self.assertEqual(value_before * 2.0, value_after)

        # area = area * factor
        address = ("2020", "Feb", "North", "A", "Sales")
        value_before = cube.get(address)

        area = cube.area("2021")
        area["Feb"] = area["Jan"] * 3.0

        value_after = cube.get(address)
        self.assertEqual(value_before * 3.0, value_after)

    def create_database(self):
        db = Database("sales", in_memory=True)

        dim_years = db.add_dimension("years")
        dim_years.edit()
        dim_years.add_member(["2020", "2021", "2022", "2023"])
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
        dim_measures.add_member(["Sales", "Cost", "Profit"])
        dim_measures.commit()

        cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products, dim_measures])

        return db, cube

    def fill_all_cells(self, cube, value=None):
        addresses = itertools.product(cube.get_dimension_by_index(0).get_leave_members(),
                                      cube.get_dimension_by_index(1).get_leave_members(),
                                      cube.get_dimension_by_index(2).get_leave_members(),
                                      cube.get_dimension_by_index(3).get_leave_members(),
                                      ["Sales", "Cost"])
        if value is None:
            for address in addresses:
                cube.set(address, float(randrange(5, 100)))
        else:
            for address in addresses:
                cube.set(address, value)




