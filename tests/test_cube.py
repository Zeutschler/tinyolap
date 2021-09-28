import gc
import math
import os
from pathlib import Path
from unittest import TestCase
import time
from database import Database
from cube import Cube
from dimension import Dimension
import itertools
from random import randrange


class TestCube(TestCase):

    def setUp(self):
        # delete database if exists
        self.database_name = "test_cube"
        self.clean_up = False

        file = os.path.join(os.getcwd(), "db", self.database_name + ".db")
        if Path(file).exists():
            os.remove(file)

    def test_create(self):

        db = Database(self.database_name)

        dim_years = db.dimension_add("years")
        dim_years.edit_begin()
        dim_years.member_add(["2020", "2021", "2022"])
        dim_years.edit_commit()

        dim_months = db.dimension_add("months")
        dim_months.edit_begin()
        dim_months.member_add(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        dim_months.member_add(["Q1", "Q2", "Q3", "Q4"],
                              [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                               ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")] )
        dim_months.member_add("Year", ("Q1", "Q2", "Q3", "Q4"))
        dim_months.edit_commit()

        dim_regions = db.dimension_add("regions")
        dim_regions.edit_begin()
        dim_regions.member_add("Total", ("North", "South", "West", "East"))
        dim_regions.edit_commit()

        dim_products = db.dimension_add("products")
        dim_products.edit_begin()
        dim_products.member_add("Total", ["A", "B", "C"])
        dim_products.edit_commit()

        measures = ["Sales", "Cost", "Profit"]
        cube = db.cube_add("sales", [dim_years, dim_months, dim_regions, dim_products], measures)
        cube.add_formula("[Profit] = [Sales] - [Cost]")

        # write, read, delete cell values by indexing
        cube["2020", "Jan", "North", "A", "Sales"] = 123.0
        value = cube["2020", "Jan", "North", "A", "Sales"]
        del cube["2020", "Jan", "North", "A", "Sales"]

        # write/read a value to/from cube
        address = ("2020", "Jan", "North", "A")
        measure = "Sales"
        cube.set(address, measure, 1.0)
        value = cube.get(address, measure)
        print(f"{address} := {value}")

        # Performance: read from cube base cells
        total = 0.0
        start = time.time()
        loops = 100_000
        for r in range(0, loops):
            total += cube.get(address, measure)
        duration = time.time() - start
        print(f"read {loops} base records in {duration:.3}sec, total = {total}")

        # write 2nd value to cube
        address = ("2020", "Feb", "North", "A")
        cube.set(address, measure, 1.0)

        # read from aggregated cells
        address = ("2020", "Q1", "Total", "Total")
        measure = "Sales"
        value = cube.get(address, measure)

        # Performance: read from aggregated cells
        total = 0.0
        start = time.time()
        loops = 100_000
        for r in range(0, loops):
            total += cube.get(address, measure)
        duration = time.time() - start
        print(f"read {loops} aggregated records in {duration:.3}sec, total = {total}")

        # read from formula cells
        address = ("2020", "Q1", "Total", "Total")
        measure = "Profit"
        value = cube.get(address, measure)

        # Performance: read from formula cells
        total = 0.0
        start = time.time()
        loops = 100_000
        for r in range(0, loops):
            total += cube.get(address, measure)
        duration = time.time() - start
        print(f"read {loops} formula records in {duration:.3}sec, total = {total}")

        # clean up
        if self.clean_up:
            db.close()
            db.remove()

    def test_cubes_of_all_dim_count_2_to_32(self):

        min_dims = 1
        max_dims = Database.MAX_DIMS

        max_loop_base_level = 1000
        max_loop_aggregation = 100

        measures = [f"measure_{i}" for i in range(0, 10)]
        base_members = [f"member_{i}" for i in range(0, 10)]

        for dims in range(min_dims, max_dims):
            db = Database(self.database_name)

            dimensions = []
            members = []
            for d in range(dims):
                dimension = db.dimension_add(f"dim_{d}")
                dimension.edit_begin()
                for member in base_members:
                    dimension.member_add(member)
                for member in base_members:
                    dimension.member_add("Total", member)
                dimension.edit_commit()

                dimensions.append(dimension)
                members.append(base_members)

            cube = db.cube_add("cube", dimensions, measures)

            # fill entire cube = (10 ^ (dims + 1) cells
            z = 0
            addresses = self.shuffle_addresses(members, max_loop_base_level)  # list(itertools.product(*members))

            start = time.time()
            for address in addresses:
                for measure in measures:
                    cube.set(address, measure, 1.0)
                    z += 1
                    if z == max_loop_base_level:
                        break
                if z == max_loop_base_level:
                    break

            duration = time.time() - start
            print(f"{dims} dimensions: {z:,.0f}x write operations in {duration:.3}sec, "
                  f"{z/float(duration):,.0f} op/sec")

            z = 0
            start = time.time()
            for address in addresses:
                for measure in measures:
                    value = cube.get(address, measure)
                    z += 1
                    if z == max_loop_base_level:
                        break
                if z == max_loop_base_level:
                    break
            duration = time.time() - start
            print(f"{dims} dimensions: {z:,.0f}x read base operations in {duration:.3}sec, "
                  f"value = {value}, {z/float(duration):,.0f} ops/sec")

            z = 0
            cube.caching = False
            start = time.time()
            total_address = tuple(["Total"] * dims)
            for i in range(max_loop_aggregation):
                for measure in measures:
                    value = cube.get(total_address, measure)
                    z += 1
                    if z == max_loop_aggregation:
                        break
                if z == max_loop_aggregation:
                    break
            duration = time.time() - start
            print(f"{dims} dimensions: {z:,.0f}x read 'total' no cache operations in {duration:.3}sec, "
                  f"value = {value}, {z/duration:,.0f} ops/sec, "
                  f"{(z * value) /duration:,.0f} aggregations/sec")
            cube.caching = True

            db.close()
            db.remove()

            gc.collect()


        # clean up
        if self.clean_up:
            db.close()
            db.remove()


    def shuffle_addresses(self, members, count):
        records = []
        for i in range(0, count):
            record = []
            for member in members:
                record.append(member[randrange(len(member))])
            records.append(record)

        return records