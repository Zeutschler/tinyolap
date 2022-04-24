# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import random
import time
import psutil
from random import randrange
from art import *

from tinyolap.database import Database
from tinyolap.slice import Slice


# adjust to your liking... and the abilities of your PC ;-)
numbers_of_records = 1_000_000
numbers_of_dimensions = 8
members_per_dimension = 100


def load_huge(console_output: bool = False):
    """
    Creates a simple but huge TinyOlap database. The intended purpose
    is to see how well a huge                                                                                                            database performs, how much memory is
    consumes and how well it uses the CPU (it does not use it well,
    it's just Python)
    """
    if console_output:
        print(f"Creating the 'huge' data model. Please wait...")

    start = time.time()
    initially_used_memory = psutil.Process().memory_info().rss / (1024 * 1024)

    # 1. create a database
    db = Database("huge", in_memory=True)

    # 2. create dimensions
    dimensions = []
    member_lists = []
    for d in range(numbers_of_dimensions):
        name = f"dim{d + 1}"
        dim = db.add_dimension(name).edit()
        members = []
        for m in range(members_per_dimension):
            member_name = f"{name}-member{m + 1}"
            dim.add_member(member_name)
            members.append(member_name)
        # create one additional aggregated member to sum up all member_defs.
        dim.add_member("All", members)
        dimensions.append(dim.commit())
        member_lists.append(members)

    # 3. Create a cube
    cube = db.add_cube("huge", dimensions)

    # lets check duration and memory consumption
    # if console_output:
    #     duration = time.time() - start
    #     actual_memory_consumption = round(psutil.Process().memory_info().rss / (1024 * 1024) - initially_used_memory, 0)
    #     print(f"\tCreating the 'huge' data model with {numbers_of_dimensions}x dimensions, "
    #           f"each with {members_per_dimension:,}x members in {duration:.3} sec.")
    #     print(f"\tMemory consumption of database without data is ±{actual_memory_consumption:,} MB.\n")

    # 4. now start the data import
    if console_output:
        print(f"Importing {numbers_of_records:,} records into the 'huge' "
              f"data model (10,000 records per dot). Please wait...")
    start = time.time()

    for r in range(numbers_of_records):
        if r > 0 and console_output and r % 10_000 == 0:
            print(".", end="")
            if console_output and r % 100_000 == 0:
                print(f" {r/numbers_of_records:.0%} ", end="")
        # create a random cell idx_address
        idx = [randrange(members_per_dimension) for d in range(numbers_of_dimensions)]
        address = tuple(members[idx[i]] for i, members in enumerate(member_lists))

        # set a value
        # we'll use 1.0 to see, how many rows have been aggregated for a specific cube value.
        cube.set(address, 1.0)

    if console_output:
        print()
        print()

    # if console_output:
    #     print()
    #     duration = time.time() - start
    #     actual_memory_consumption = round(psutil.Process().memory_info().rss / (1024 * 1024) - initially_used_memory, 0)
    #     print(f"\tImporting {numbers_of_records:,} records into the 'huge' data model in {duration:.3} sec.")
    #     print(f"\tMemory consumption of database including {cube.cells_count:,} values "
    #       f"is ±{actual_memory_consumption:,} MB, "
    #       f"±{round(actual_memory_consumption / cube.cells_count * 1000, 2)} kB per value.\n")

    # That's it...
    return db, cube, dimensions, member_lists


def play_huge(console_output: bool = True):
    """ Demonstrates the creation and usage of a 'huge' database cube."""

    if console_output:
        tprint("TinyOlap",font="Slant")

    # 1. create and load the database
    database, cube, dimensions, member_lists = load_huge(console_output)

    # 2. do some reports (cache is cold o first queries)
    # of the dimension will be selected and used.
    title = f"Report on 'huge' database with {numbers_of_dimensions} dimensions, containing {cube.cells_count:,} values"
    headers = [{"dimension": dimension.name, "member": "All"} for dimension in dimensions[:numbers_of_dimensions - 3]]
    rows = [{"dimension": dimensions[numbers_of_dimensions - 2].name, "member": "All"}]
    # columns = [{"dimension": dimensions[-1].name, "member": member_lists[-1]}]
    columns = [{"dimension": dimensions[-1].name, "member": "All"}]
    report_definition = {"title": title, "header": headers, "columns": columns, "rows": rows}
    start = time.time()

    report = Slice(cube, report_definition)

    if console_output:
        duration = time.time() - start
        print(report)
        print(f"\nReport was executed in {duration:.3} sec on cloud cache, {int(cube.cells_count/duration):,} aggregations/sec")

        start = time.time()
        report.refresh()
        duration = time.time() - start
        print(f"Report was executed in {duration:.3} sec on warm cache, 0 aggregations/sec")

        print(f"\nNote: The actual numbers of records in the cube is {cube.cells_count:,}."
              f"\n      In rare cases, this number might by below the expected {numbers_of_records:,} number of records."
              f"\n      Reason: randomly generated cell addresses might have create duplicate addresses.")


def benchmark_load_database(console_output: bool = True):

    initially_used_memory = psutil.Process().memory_info().rss / (1024 * 1024)
    start = time.time()

    database, cube, dimensions, member_lists = load_huge(console_output)

    duration = time.time() - start
    actual_memory_consumption = round(psutil.Process().memory_info().rss / (1024 * 1024) - initially_used_memory, 0)
    print(f"Importing {numbers_of_records:,} records into the 'huge' data model "
          f"in {duration:.6} sec, {round(numbers_of_records/duration, 0):,} ops/sec, ")
    print(f"Memory consumption of database including {cube.cells_count:,} values "
          f"is ±{actual_memory_consumption:,} MB, "
          f"±{round(actual_memory_consumption / cube.cells_count * 1000, 2)} kB per value.\n")

    return database, cube, dimensions, member_lists


def benchmark_read_random_base_cells(cube, dimensions, loops: int = 10_000, console_output: bool = True):
    address = []
    while True:
        address = [dim.get_leaves()[random.randrange(0, len(dim.get_leaves()))] for dim in dimensions]
        value = cube.get(address)
        if value is None or value == 0.0:
            break

    start = time.time()
    for l in range(loops):
        value = cube.get(address)
    duration = time.time() - start
    print(f"Reading non-existing base level cell {loops:,}x times from 'huge' data model "
          f"in {duration:.6} sec, {round(loops/duration, 0):,} ops/sec, ")

    cube.set(address, 1.0)
    start = time.time()
    for l in range(loops):
        value = cube.get(address)
    duration = time.time() - start
    print(f"Reading existing base level cell {loops:,}x times from 'huge' data model "
          f"in {duration:.6} sec, {round(loops/duration, 0):,} ops/sec, ")


def benchmark_read_top_cells(cube, dimensions, loops: int = 10, console_output: bool = True):
    address = ["All" for dim in dimensions]
    cube.caching = False
    value = 0.0
    start = time.time()
    for l in range(loops):
        value = cube.get(address)
    duration = time.time() - start
    print(f"Reading top level cell {loops:,}x times from 'huge' data model "
          f"in {duration:.6} sec, {round((loops * value)/duration, 0):,} ops/sec, ")


def benchmark(console_output: bool = True):
    # 1. create and load the database

    database, cube, dimensions, member_lists = benchmark_load_database(console_output)
    benchmark_read_random_base_cells(cube, dimensions,10_000, console_output)
    benchmark_read_top_cells(cube, dimensions, 10, console_output)



def main():
    # play_huge()
    benchmark(True)


if __name__ == "__main__":
    main()
