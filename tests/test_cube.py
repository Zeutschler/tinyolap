from unittest import TestCase
import os
from pathlib import Path
import time

from rules import RuleError
from tinyolap.database import Database
from tinyolap.cube import Cube
from tinyolap.dimension import Dimension
from random import randrange


class TestCube(TestCase):

    def setUp(self):
        # delete database if exists
        self.database_name = "test_cube"
        self.clean_up = False

        file = os.path.join(os.getcwd(), "db", self.database_name + ".db")
        if Path(file).exists():
            os.remove(file)

    def tearDown(self) -> None:

        # delete database if exists
        file = os.path.join(os.getcwd(), "db", self.database_name + ".db")
        if Path(file).exists():
            os.remove(file)

    def test_create(self,  console_output: bool = False):

        db = Database(self.database_name, in_memory=True)

        dim_years = db.add_dimension("years")
        dim_years.edit()
        dim_years.add_many(["2020", "2021", "2022"])
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

        measures = ["Sales", "Cost", "Profit"]
        cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products, dim_measures])
        # todo: Uppps, not yet supported for measures...
        cube.register_rule(lambda x: x["Sales"] - x["Cost"], "Profit")
        cube.register_rule(lambda x: x["Jan"] - x["Feb"], "Q1")
        cube.register_rule(lambda x: x["Jan"] / 0.0, "Mar")  # a rule which always throws a #DIV0 error
        cube.register_rule(lambda x: x["xzy"] * 2.0, "Apr")  # a rule which always throws a #REF error
        cube.register_rule(lambda x: x[True] * 2.0, "Mai")  # a rule which always throws a #ERR error

        # disable caching
        cube.caching = False

        # write, read, delete cell values by indexing
        cube["2020", "Jan", "North", "A", "Sales"] = 123.0
        value = cube["2020", "Jan", "North", "A", "Sales"]
        del cube["2020", "Jan", "North", "A", "Sales"]

        # access rule with error
        value = cube["2020", "Mar", "North", "A", "Sales"]
        self.assertEqual(value.value, RuleError.DIV0.value)
        value = cube["2020", "Apr", "North", "A", "Sales"]
        self.assertEqual(value.value, RuleError.REF.value)
        value = cube["2020", "Mai", "North", "A", "Sales"]
        self.assertEqual(value.value, RuleError.ERR.value)


        # write/read a value to/from cube
        address = ("2020", "Jan", "North", "A", "Sales")
        cube.set(address, 1.0)
        value = cube.get(address)
        if console_output:
            print(f"{address} := {value}")

        max_loops = 1_000
        # Performance: read from cube base cells
        total = 0.0
        start = time.time()
        loops = max(1_000, max_loops)
        for r in range(0, loops):
            total += cube.get(address)
        duration = time.time() - start
        if console_output:
            print(f"read {loops} base records in {duration:.3}sec, total = {total}")

        # write 2nd value to cube
        address = ("2020", "Feb", "North", "A", "Sales")
        cube.set(address, 1.0)

        # read from aggregated cells
        address = ("2020", "Q1", "Total", "Total", "Sales")
        value = cube.get(address)

        # Performance: read from aggregated cells
        total = 0.0
        start = time.time()
        loops = max(1_000, max_loops)
        for r in range(0, loops):
            total += cube.get(address)
        duration = time.time() - start
        if console_output:
            print(f"read {loops} aggregated records in {duration:.3}sec, total = {total}")

        # read from formula cells
        address = ("2020", "Q1", "Total", "Total", "Profit")
        value = cube.get(address)

        # Performance: read from formula cells
        total = 0.0
        start = time.time()
        loops = max(1_000, max_loops)
        for r in range(0, loops):
            total += cube.get(address)
        duration = time.time() - start
        if console_output:
            print(f"read {loops} formula records in {duration:.3}sec, total = {total}")

        # clean up
        if self.clean_up:
            db.close()
            db.delete()

    def test_big_cube(self,  console_output: bool = False):
        min_dims = 3
        max_dims = 8
        base_members = [f"member_{i}" for i in range(0, 100)]
        max_loop_base_level = 100
        max_loop_aggregation = 100

        for dims in range(min_dims, max_dims):
            db = Database("test", in_memory=True)

            dimensions = []
            members = []
            for d in range(dims):
                dimension = db.add_dimension(f"dim_{d}")
                dimension.edit()
                for member in base_members:
                    dimension.add_many(member)
                for member in base_members:
                    dimension.add_many("Total", member)
                dimension.commit()
                dimensions.append(dimension)
                members.append(base_members)
            cube = db.add_cube("cube", dimensions)

            if console_output:
                print(f"Cube with {dims} dimensions sized {', '.join(str(len(d)) for  d in dimensions)} : ")

            z = max_loop_base_level
            value = 0
            addresses = self.shuffle_addresses(members, max_loop_base_level)

            start = time.time()
            for address in addresses:
                cube.set(address, 1.0)
            duration = time.time() - start
            if console_output:
                print(f"\t{z:,.0f}x write operations by 'set(...)' in {duration:.3}sec, "
                      f"{z / float(duration):,.0f} op/sec")

            start = time.time()
            for address in addresses:
                value = cube.get(address)
            duration = time.time() - start
            if console_output:
                print(f"\t{z:,.0f}x read base-level cells in {duration:.3}sec, "
                      f"value = {value}, {z / float(duration):,.0f} ops/sec")

            cube.caching = False
            start = time.time()
            total_address = ["Total"] * dims
            total_address = tuple(total_address)
            for i in range(max_loop_aggregation):
                value = cube.get(total_address)
            duration = time.time() - start
            if console_output:
                print(f"\t{max_loop_aggregation:,.0f}x read aggregated cell (no cache operations) in {duration:.3}sec, "
                      f"value = {value}, {max_loop_aggregation / duration:,.0f} ops/sec, "
                      f"{(max_loop_aggregation * value) / duration:,.0f} aggregations/sec")
            cube.caching = True

    def shuffle_addresses(self, members,  count):
        records = []
        for i in range(0, count):
            record = []
            for member in members:
                record.append(member[randrange(len(member))])
            records.append(record)

        return tuple(records)
