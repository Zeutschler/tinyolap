import gc
import math
from unittest import TestCase
import time
from database import Database
from cube import Cube
from dimension import Dimension
import itertools


class TestCube(TestCase):

    def test_create(self):

        db = Database("test_temp")

        dim_years = db.dimension_add("Years")
        dim_years.edit_begin()
        dim_years.member_add(["2020", "2021", "2022"])
        dim_years.edit_commit()

        dim_months = db.dimension_add("Months")
        dim_months.edit_begin()
        dim_months.member_add(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        dim_months.member_add(["Q1", "Q2", "Q3", "Q4"],
                              [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                               ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")] )
        dim_months.member_add("Year", ("Q1", "Q2", "Q3", "Q4"))
        dim_months.edit_commit()

        dim_regions = db.dimension_add("Regions")
        dim_regions.edit_begin()
        dim_regions.member_add("Total", ("North", "South", "West", "East"))
        dim_regions.edit_commit()

        dim_products = db.dimension_add("Products")
        dim_products.edit_begin()
        dim_products.member_add("Total", ["A", "B", "C"])
        dim_products.edit_commit()

        measures = ["Sales", "Cost", "Profit"]
        cube = db.cube_add("Sales", [dim_years, dim_months, dim_regions, dim_products], measures)
        cube.add_formula("[Profit] = [Sales] - [Cost]")

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
        db.close()
        db.remove()

    def test_big_cube(self):

        min_dims = 2
        max_dims = 8
        measures = [f"measure_{i}" for i in range(0, 10)]
        base_members = [f"member_{i}" for i in range(0, 10)]

        db = Database("test_temp")

        for dims in range(min_dims, max_dims):
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
            addresses = list(itertools.product(*members))
            start = time.time()
            for address in addresses:
                for measure in measures:
                    cube.set(address, measure, 1.0)
                    z += 1
                    if z == 10000:
                        break
                if z == 10000:
                    break

            duration = time.time() - start
            print(f"{dims} dimensions: {z:,.0f}x write operations in {duration:.3}sec, "
                  f"{math.pow(10, dims + 1)/float(duration):,.0f} op/sec")

            z = 0
            start = time.time()
            for address in addresses:
                for measure in measures:
                    value = cube.get(address, measure)
                    z += 1
                    if z == 10000:
                        break
                if z == 10000:
                    break
            duration = time.time() - start
            print(f"{dims} dimensions: {z:,.0f}x read base operations in {duration:.3}sec, "
                  f"value = {value}, {z/float(duration):,.0f} ops/sec")

            z = 0
            cube.deactivate_caching()
            start = time.time()
            total_address = tuple(["Total"] * dims)
            for i in range(1000):
                for measure in measures:
                    value = cube.get(total_address, measure)
                    z += 1
                    if z == 1000:
                        break
                if z == 1000:
                    break
            duration = time.time() - start
            print(f"{dims} dimensions: {z:,.0f}x read 'total' no cache operations in {duration:.3}sec, "
                  f"value = {value}, {z/duration:,.0f} ops/sec, "
                  f"{(z * value) /duration:,.0f} aggregations/sec")
            cube.activate_caching()

            cube = None
            gc.collect()

        # clean up
        db.close()
        db.remove()
