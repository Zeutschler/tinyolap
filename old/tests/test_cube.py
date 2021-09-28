import gc
import math
import sys
from unittest import TestCase
import time
from old.cube import Cube
from old.dimension import Dimension
import itertools
from random import randrange

class TestCube(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create(self):

        dim_years = Dimension("Years")
        dim_years.member_add("2020")
        dim_years.member_add("2021")
        dim_years.member_add("2022")

        # self.assertTrue(self.execute(Test.EXPECTED_RESULT), True)

        dim_months = Dimension("Months")
        dim_months.member_add("Jan", "Q1")
        dim_months.member_add("Feb", "Q1")
        dim_months.member_add("Mar", "Q1")
        dim_months.member_add("Apr", "Q2")
        dim_months.member_add("Mai", "Q2")
        dim_months.member_add("Jun", "Q2")
        dim_months.member_add("Jul", "Q3")
        dim_months.member_add("Aug", "Q3")
        dim_months.member_add("Sep", "Q3")
        dim_months.member_add("Oct", "Q4")
        dim_months.member_add("Noc", "Q4")
        dim_months.member_add("Dec", "Q4")
        dim_months.member_add("Q1", "Year")
        dim_months.member_add("Q2", "Year")
        dim_months.member_add("Q3", "Year")
        dim_months.member_add("Q4", "Year")

        dim_regions = Dimension("Regions")
        dim_regions.member_add("North", "Total")
        dim_regions.member_add("South", "Total")
        dim_regions.member_add("West", "Total")
        dim_regions.member_add("East", "Total")

        dim_products = Dimension("Products")
        dim_products.member_add("A", "Total")
        dim_products.member_add("B", "Total")
        dim_products.member_add("C", "Total")

        measures = ["Sales", "Cost", "Profit"]
        cube = Cube("Sales", [dim_years, dim_months, dim_regions, dim_products], measures)
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

        # Performance: read from aggreagted cells
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

    def test_big_cube(self):

        min_dims = 2
        max_dims = 32
        measures = [f"measure_{i}" for i in range(0, 10)]
        base_members = [f"member_{i}" for i in range(0, 10)]
        max_loop_base_level = 1000
        max_loop_aggregation = 100
        
        for dims in range(min_dims, max_dims):
            dimensions = []
            members = []
            for d in range(dims):
                dimension = Dimension(f"dim_{d}")
                for member in base_members:
                    dimension.member_add(member)
                for member in base_members:
                    dimension.member_add(member, "Total")
                dimensions.append(dimension)
                members.append(base_members)
            cube = Cube("cube", dimensions, measures)

            # fill entire cube = (10 ^ (dims + 1) cells
            z=0
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

            z=0
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

            z=0
            cube.deactivate_caching()
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
            cube.activate_caching()

            cube = None
            gc.collect()

        time.sleep(0.1)

    def test_one_million_cells(self):

        max_dims = 3
        measures = [f"measure_{i}" for i in range(0, 10)]
        base_members = [f"member_{i}" for i in range(0, 10)]

        dimensions = []
        members = []
        for d in range(max_dims):
            dimension = Dimension(f"dim_{d}")
            for member in base_members:
                dimension.member_add(member)
            for member in base_members:
                dimension.member_add(member, "Total")
            dimensions.append(dimension)
            members.append(base_members)
        cube = Cube("cube", dimensions, measures)

        # fill entire cube = (10 ^ (dims + 1) cells
        z = 0
        addresses = list(itertools.product(*members))
        start = time.time()
        start_sub = time.time()
        for address in addresses:
            for measure in measures:
                cube.set(address, measure, 1.0)
                z += 1
                if z % 100000 == 0:
                    duration = time.time() - start_sub
                    print(f"   {z/len(addresses)/10:0.0%} {100000 / float(duration):,.0f} op/sec")
                    start_sub = time.time()

        duration = time.time() - start
        print(f"{max_dims} dimensions: {z:,.0f}x write operations in {duration:.3}sec, "
              f"{z / float(duration):,.0f} op/sec")

        z = 0
        start = time.time()
        for address in addresses:
            for measure in measures:
                value = cube.get(address, measure)
                z += 1
                if z % 100000 == 0:
                    duration = time.time() - start_sub
                    print(f"   {z/len(addresses)/10:0%} {100000 / float(duration):,.0f} op/sec")
                    start_sub = time.time()

        duration = time.time() - start
        print(f"{max_dims} dimensions: {z:,.0f}x read base operations in {duration:.3}sec, "
              f"value = {value}, {z / float(duration):,.0f} ops/sec")

        z = 0
        cube.deactivate_caching()
        start = time.time()
        total_address = tuple(["Total"] * max_dims)
        for i in range(10):
            for measure in measures:
                value = cube.get(total_address, measure)
                z += 1
                duration = time.time() - start_sub
                print(f"   {z/len(addresses)/10:0%} {10 / float(duration):,.0f} op/sec")
                start_sub = time.time()
        duration = time.time() - start
        print(f"{max_dims} dimensions: {z:,.0f}x read 'total' no cache operations in {duration:.3}sec, "
              f"value = {value}, {z / duration:,.0f} ops/sec, "
              f"{(z * value) / duration:,.0f} aggregations/sec")
        cube.activate_caching()

        gc.collect()
        time.sleep(0.1)

    def shuffle_addresses(self, members, count):
        records = []
        for i in range(0, count):
            record = []
            for member in members:
                record.append(member[randrange(len(member))])
            records.append(record)

        return records