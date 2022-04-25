import random

from tinyolap.cube import Cube
from tinyolap.server import Server
from tinyolap.database import Database
from tinyolap.view import View

# region Create a very small sample database
dim1 = ["2021", "2022", "2023"]
dim2 = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
dim3 = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
dim4 = ["X", "Z", "Y"]
members = [dim1, dim2, dim3, dim4]
def very_small_sample_db() -> Database:
    db = Database("db")
    cube = db.add_cube("cube", [
        create_dim(db, "dim1", dim1),
        create_dim(db, "dim2", dim2),
        create_dim(db, "dim3", dim3),
        create_dim(db, "dim4", dim4)
    ])
    for i in range(100):
        cube.set([members[d][random.randrange(0,len(members[d]))]
                  for d in range(len(members))], round(random.random() * 1000.0, 0))
    return db
def create_dim(db, name, members):
    dim = db.add_dimension(name).edit()
    for member in members:
        dim.add_member(str(member))
    dim.add_member("All", members)
    dim.commit()
    return dim
# endregion


# API functions
def random_read(db: Database) -> (str, str, list[str], float):
    cube = db.cubes["cube"]
    address = [members[d][random.randrange(0,len(members[d]))]
                  for d in range(len(members))]
    value = cube[address]
    return db.name, cube.name, address, value


def random_write(db: Database) -> (str, str, list[str], float):
    cube = db.cubes["cube"]
    address = [members[d][random.randrange(0,len(members[d]))]
                  for d in range(len(members))]
    value = round(random.random() * 1000.0, 0)
    cube[address] = value
    value = cube[address]
    return db.name, cube.name, address, value


def create_view(cube: Cube) -> View:
    return View(cube)


# endregion