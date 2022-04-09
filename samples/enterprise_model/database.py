# Purpose: Creation of the Enterprise sample database.
import datetime
import os.path

from faker import Faker

from dimension import Dimension
from tinyolap.database import Database

def create_database(name: str = "enterprise", database_directory: str = None,
                    num_legal_entities: int = 50, num_products: int = 100,
                    num_employees: int = 1_000):
    """
    Creates a new Enterprise sample database instance.
    :param name: The name of the database.
    :param database_directory: The file location for the database. If not provided, an in-memory data will be created.
    :param num_legal_entities: : Defines the number of legal entities the enterprise should have.
    :param num_products: : Defines the number of legal products the enterprise should have.
    :param num_employees: : Defines the number of employees the enterprise should have.
    :return: The created enterprise database.
    """

    # setup the database
    if not database_directory:
        db = Database(name=name, in_memory=True)
    else:
        db = Database(name=os.path.join(database_directory, name, ".db"))

    # setup dimensions
    add_dimension_datatype(db)
    add_dimension_years(db)
    add_dimension_periods(db)

    # Cubes: PL, Sales, HR, CurConv
    return db


def populate_database(db: Database):
    """Populates the Enterprise sample database with data."""
    pass


# region Dimension Creation
def add_dimension_periods(db: Database, name: str = "periods") -> Dimension:
    """
    Dimension defining the periods of the year: months, quarters half-years and year
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """

    d = db.add_dimension(name).edit()
    d.add_member(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    d.add_member(["Q1", "Q2", "Q3", "Q4"],
                 [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                  ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
    d.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
    d.add_member(["HY1", "HY2"], [("Q1", "Q2"), ("Q3", "Q4")])
    return d.commit()


def add_dimension_years(db: Database, name: str = "years",
                        first: int = datetime.datetime.now().year - 3,
                        last: int = datetime.datetime.now().year + 3) -> Dimension:
    """
    Dimension defining the years to be contained in the data model. By default,
    the current year +/-3 years will be created.
    :param db: The target database.
    :param name: Name of the dimension
    :param first: First year of the dimension
    :param last: Last year of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    if last < first:
        last = first
    for y in range(first, last + 1):
        d.add_member(str(y))
    return d.commit()


def add_dimension_datatype(db: Database, name: str = "datatype") -> Dimension:
    """
    Dimension defining the data types to be contained in the data model:
      Actual := Actual figures
      Plan := Planned figures
      Forecast := Forecastes figures
      DevPlan, DevFC := Deviation of actual vs forecast (rules required)
      DevPlan%, DevFC% := Deviation of actual vs forecast in percent (rules required)
      DevPY := Delta previous year (rule required)
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    d.add_member(["Actual", "Plan", "Forecast",
                  "DevPlan", "DevPlan%",
                  "ActVsFC", "ActVsFC%",
                  "ActVsPY","ActVsPY%"])
    return d.commit()


def add_dimension_pl(db: Database, name: str = "pl") -> Dimension:
    """
    Dimension defining the chart of account for a profit & loss statement:
    The chart of account and the required calcuation logic are maintained in a speparate file.
    Will also dynamically create rule from that file. Better than to type all the rules by hand.

    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    d.add_member(["Actual", "Plan", "Forecast",
                  "ActVsPlan", "ActVsPlan%",
                  "ActVsFC", "ActVsFC%",
                  "ActVsPY","ActVsPY%"])
    return d.commit()

# endregion
