from unittest import TestCase

from dimension import Dimension
from slice import Slice
from tinyolap.database import Database
from pathlib import Path
import os
import time


class Test(TestCase):

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_set_operations(self):

        loops = 1000
        sizes = (1, 5, 10, 50, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000)
        sets = [set(range(s)) for s in sizes]

        # optimal order
        start = time.time()
        result = set([])
        for i in range(loops):
            result = sets[0]
            for s in range(1, len(sets)):
                result = result.intersection(sets[s])
        best_duration = time.time() - start
        print(f"Best case intersection returning {len(result)} items in {best_duration:.4}sec")

        # worst order
        sets.reverse()
        start = time.time()
        result = set([])
        for i in range(loops):
            result = sets[0]
            for s in range(1, len(sets)):
                result = result.intersection(sets[s])
        worst_duration = time.time() - start
        print(f"Worst case intersection returning {len(result)} items in {worst_duration:.4}sec")
        print(f"Best is {int(worst_duration / best_duration):,}x times faster than worst")

    def test_load_alea_tutor(self):

        db_name = "tutor"
        db = Database(db_name, in_memory=True)
        cube_name = "verkauf"
        measures = ("value", "count")
        m_value = measures[0]
        m_count = measures[1]
        dims = ["jahre", "datenart", "regionen", "produkte", "monate", "wertart"]
        dim_count = len(dims)
        dimensions = []
        root_path = os.path.abspath(os.path.join(os.getcwd(), os.pardir))

        # 1. read dimension
        start = time.time()
        for dim in dims:
            file_name = os.path.join(root_path, "data", "alea_tutor", dim.upper() + ".TXT")
            dim = db.add_dimension(dim)
            dim.edit()
            empty_rows = 0
            parent = ""
            codec = 'latin-1'
            with open(file_name, encoding=codec) as file:
                while record := [t.strip() for t in file.readline().rstrip().split("\t")]:
                    if len(record) == 1:
                        empty_rows += 1
                        if empty_rows > 5:
                            break
                        continue

                    level = record[0]
                    member = record[1]
                    if len(record) > 2:
                        weight = float(record[2])
                    else:
                        weight = 1.0

                    if level == "C":
                        dim.add_member(member)
                        parent = member
                    elif level == "N":
                        dim.add_member(member)
                    else:
                        dim.add_member(parent, member)
            dim.commit()
            dimensions.append(dim)

        # 2. validate dimensions
        # self.validate_dimension(dimensions)

        # 3. create cube
        cube = db.add_cube(cube_name, dimensions, measures)
        duration = time.time() - start
        print(f"Create database {db_name} in {duration:.4}sec")

        # 4. import data (first into an array)
        start = time.time()
        file_name = os.path.join(root_path, "data", "alea_tutor", cube_name.upper() + ".TXT")
        codec = 'latin-1'
        empty_rows = 0
        z = 0
        with open(file_name, encoding=codec) as file:
            while record := [t.strip() for t in file.readline().rstrip().split("\t")]:
                if len(record) == 1:
                    empty_rows += 1
                    if empty_rows > 5:
                        break
                    continue
                address = tuple(record[: dim_count])
                value = float(record[dim_count])
                cube.set(address, value)
                z += 1

        duration = time.time() - start
        print(f"{z}x records imported into database {db_name} in {duration:.4}sec")

        # 5. read aggregated cell
        cube.caching = False
        addresses = [("Alle Jahre", "Abweichung", "Welt gesamt", "Produkte gesamt", "Jahr gesamt", "DB1", "value"),
                     ("1994", "Ist", "Welt gesamt", "Produkte gesamt", "Jahr gesamt", "Umsatz", "value"),
                     ("1994", "Ist", "Welt gesamt", "Produkte gesamt", "Januar", "Umsatz", "value"),
                     ("1994", "Ist", "USA", "Produkte gesamt", "Januar", "Umsatz", "value")]

        for address in addresses:
            cube.reset_cell_requests()
            total = 0.0
            value = 0.0
            start = time.time()
            for i in range(100):
                value = cube.get(address)
                total += value
            duration = time.time() - start
            print(f"read {1000}x aggregated cell returning value := {value}, ")
            print(f"\toverall {cube.cell_requests:,} aggregations in {duration:.4} sec, ")
            print(f"\t{int(1000 / duration):,} ops/sec, {int(cube.cell_requests / duration):,} agg/sec")

        # 6. Create a sample slice
        cube.caching = False
        definitions = [("high aggregation", 10, {"columns": [{"dimension": "jahre"}], "rows": [{"dimension": "monate"}]}),
                       ("mid aggregation", 50, {"header": [{"dimension": "datenart", "member": "Ist"},
                                                       {"dimension": "regionen", "member": "USA"},
                                                       {"dimension": "produkte", "member": "Produkte gesamt"},
                                                       {"dimension": "wertart", "member": "Umsatz"}],
                                            "columns": [{"dimension": "jahre"}], "rows": [{"dimension": "monate"}]}),
                       ("low aggregation", 100, {"header": [{"dimension": "datenart", "member": "Ist"},
                                                       {"dimension": "regionen", "member": "USA"},
                                                       {"dimension": "produkte", "member": "ProView VGA 15"},
                                                       {"dimension": "wertart", "member": "Umsatz"}],
                                            "columns": [{"dimension": "jahre"}], "rows": [{"dimension": "monate"}]})]
        print("\r\nSLICE RENDERING")
        for report in definitions:
            loops = report[1]
            cube.reset_cell_requests()
            slice = ""
            start = time.time()
            for i in range(loops):
                slice = Slice(cube, report[2])
            duration = time.time() - start
            print(f"Rendering {report[0]} slice {loops}x times in {duration:.4} sec, "
                  f"{int(loops / duration):,} slices/sec, {duration / loops:.4} per slice, "
                  f"{int(cube.cell_requests / duration):,} cell-requests/sec")
            # print(slice)

        db.close()
        db.delete()

    def validate_dimension(self, dimensions: list[Dimension]):
        for dim in dimensions:
            print(f"Dimension '{dim.name}'")
            roots = dim.get_root_members()
            print(f"\troot members: {roots}")

            leafs = dim.get_leave_members()
            print(f"\tleaf members: {leafs}")

            print(f"\tHierarchies: {leafs}")
            for root in roots:
                self.print_children(dim, root)

    def print_children(self, dimension: Dimension, member, depth=2):
        indent = '\t'
        print(f"{indent * depth}{member} [{dimension.member_get_index(member)}]")
        if dimension.member_get_level(member) > 0:
            children = dimension.member_get_children(member)
            for child in children:
                self.print_children(dimension, child, depth + 1)
