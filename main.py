from database import Database
from dimension import Dimension

# Create or open a database
db = Database("test")

if len(db.dimensions) > 0:
    names = list(db.dimensions.keys())
    for d in names:
        db.dimension_remove(d)

if db.dimension_exists("years"):
    db.dimension_remove("years")


# A flat dimension, members have no parents and therefore no aggregation hierarchy.
dim_years = db.dimension_add("years")

# add some members
dim_years.edit_begin()
dim_years.member_add("2020")
dim_years.member_add(["2021", "2022"])
dim_years.member_add("All years", "2020")
dim_years.member_add("All years", ["2021", "2022"])
dim_years.edit_commit()

# add again some members
dim_years.edit_begin()
dim_years.member_add("2023")
dim_years.member_add("All years", "2023")
dim_years.edit_rollback()

db.close()