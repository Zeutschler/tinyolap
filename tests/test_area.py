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

        # valid data area definitions (no error should occur)
        area = cube.area("2021")
        area = cube.area("2021", "months:Jan", "3:A")
        area = cube.area(["2021", "2022"], "months:Jan", "3:A")
        area = cube.area(["2021", "2022"], "months:Jan", ("A", "C"))
        area = cube.area(["2021", "2022"], "months:Jan", ("products:Total",))

        with self.assertRaises(Exception):
            area = cube.area(123)  # wrong data type

        with self.assertRaises(Exception):
            area = cube.area(["2021", "2022"], ["2022", "2023"])  # multiple use of a dimension

    def test_area_create_modify_clear(self):

        cube = self.cube
        self.fill_all_cells(cube, 1.0)

        # read from aggregated cells
        address = ("2020", "Q1", "Total", "Total", "Sales")
        value_before = cube.get(address)

        # 1. create area
        area = cube.area("2021")

        # 2. evaluate min, max, avg
        self.assertEqual(1.0, area.min())
        self.assertEqual(1.0, area.max())
        self.assertEqual(1.0, area.avg())

        # 3. multiply -> evaluate min, max, avg
        area.multiply(2.0)
        self.assertEqual(2.0, area.min())
        self.assertEqual(2.0, area.max())
        self.assertEqual(2.0, area.avg())

        # 4. increment -> evaluate min, max, avg
        area.increment(1.0)
        self.assertEqual(3.0, area.min())
        self.assertEqual(3.0, area.max())
        self.assertEqual(3.0, area.avg())

        # 5. sum
        value = area.sum()
        self.assertEqual(864.0, value)

        # 6. clear values (remove all records and update all indexes)
        rows = len(area)
        self.assertEqual(288, rows)

        area.clear()

        rows = len(area)
        self.assertEqual(0, rows)

    def test_area_loops_over_records(self):
        cube = self.cube
        cube.clear()
        self.fill_all_cells(cube, 1.0)

        area = cube.area("2021", "Jan")

        total = 0.0
        for record in area.records(include_cube_name=True, as_list=True):
            total += record[-1]
        self.assertEqual(area.sum(), total)

        addresses = []
        for address in area.addresses():
            addresses.append(address)
        self.assertEqual(len(area), len(addresses))


    def test_area_math(self):

        cube = self.cube
        cube.clear()
        self.fill_all_cells(cube, 1.0)

        # an address from within target range 'Feb"
        address = ("2020", "Feb", "North", "A", "Sales")
        value_before = cube.get(address)
        self.assertEqual(1.0, value_before)

        area = cube.area("2020")
        bera = cube.area()

        # copy a modified source area to a target area
        area["Feb"] = area["Jan"] * 3.0
        value_after = cube.get(address)
        self.assertEqual(3.0, value_after)

        # direct mathematical operations
        area["Feb"] /= 3.0
        value_after = cube.get(address)
        self.assertEqual(1.0, value_after)

        area["Feb"] += 4.0
        value_after = cube.get(address)
        self.assertEqual(5.0, value_after)

        area["Feb"] -= 2.0
        value_after = cube.get(address)
        self.assertEqual(3.0, value_after)

        with self.assertRaises(Exception):
            area["Feb"] = area["2021"]  # different dimensions


        with self.assertRaises(Exception):
            area["2020", "Feb"] = area["Jan", "2021"]  # different dimensions
        with self.assertRaises(Exception):
            area["Feb"] = area["Jan", "2021"]  # different dimensions

        area["Feb", "2022"] = area["Jan", "2021"]  # correct = matching dimensions

    def create_database(self):
        db = Database("sales", in_memory=True)

        dim_years = db.add_dimension("years")
        dim_years.edit()
        dim_years.add_many(["2020", "2021", "2022", "2023"])
        dim_years.commit()

        dim_months = db.add_dimension("months")
        dim_months.edit()
        dim_months.add_many(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        dim_months.add_many(["Q1", "Q2", "Q3", "Q4"],
                            [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                               ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
        dim_months.add_many("Year", ("Q1", "Q2", "Q3", "Q4"))
        dim_months.commit()

        dim_regions = db.add_dimension("regions")
        dim_regions.edit()
        dim_regions.add_many("Total", ("North", "South", "West", "East"))
        dim_regions.commit()

        dim_products = db.add_dimension("products")
        dim_products.edit()
        dim_products.add_many("Total", ["A", "B", "C"])
        dim_products.commit()

        dim_measures = db.add_dimension("measures")
        dim_measures.edit()
        dim_measures.add_many(["Sales", "Cost", "Profit"])
        dim_measures.commit()

        cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products, dim_measures])

        return db, cube

    def fill_all_cells(self, cube, value=None):
        addresses = itertools.product(cube.get_dimension_by_index(0).get_leaves(),
                                      cube.get_dimension_by_index(1).get_leaves(),
                                      cube.get_dimension_by_index(2).get_leaves(),
                                      cube.get_dimension_by_index(3).get_leaves(),
                                      ["Sales", "Cost"])
        if value is None:
            for address in addresses:
                cube.set(address, float(randrange(5, 100)))
        else:
            for address in addresses:
                cube.set(address, value)




