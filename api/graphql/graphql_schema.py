# The TinyOlap GraphQl schema
import random

from tinyolap.database import Database


def tinyolap_gql():
    return """
    scalar JSON
    type Cell {
        db: String,
        cube: String!
        address: [String!]
        value: Float!
    }
    type Query {
        read(
            db: String,
            cube: String!,
            address: [String!]
        ): Cell!
        random_read: Cell!
        random_write: Cell!
    }
    type Mutation {
        write(
            db: String,
            cube: String!,
            address: [String!],
            value: Float!
        ): Boolean!
    }
    """


dim1 = ["2021", "2022", "2023"]
dim2 = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
dim3 = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
dim4 = ["X", "Z", "Y"]
members = [dim1, dim2, dim3, dim4]
def tinyolap_db() -> Database:
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
        dim.add_many(str(member))
    dim.add_many("All", members)
    dim.commit()
    return dim

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