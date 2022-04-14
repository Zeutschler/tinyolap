# Purpose: Creation of the Enterprise sample database.
import datetime
import math
import os.path

import random
from faker import Faker
from faker.providers.company import Provider as company_provider

from tinyolap.dimension import Dimension
from tinyolap.decorators import rule
from tinyolap.database import Database
from tinyolap.database import Cube
from tinyolap.rules import RuleScope, RuleInjectionStrategy
from tinyolap.area import Area
from tinyolap.cell import Cell


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
    datatype = add_dimension_datatype(db)
    years = add_dimension_years(db)
    periods = add_dimension_periods(db)
    company = add_dimension_company(db, companies_count=num_legal_entities)
    pnl = add_dimension_pnl_statement(db)

    # setup cubes 'PL'
    pnl_cube = db.add_cube("pnl", [datatype, years, periods, company, pnl])
    rules_functions = [rule_datatype_actvspl, rule_datatype_actvspl_percent,
                       rule_datatype_actvsfc, rule_datatype_actvsfc_percent,
                       rule_datatype_fcvspl, rule_datatype_fcvspl_percent,
                       rule_datatype_fcvsactpy, rule_datatype_fcvsactpy_percent,
                       rule_datatype_actvactpy, rule_datatype_actvactpy_percent]
    for func in rules_functions:
        pnl_cube.register_rule(func)
    populate_cube_pnl(db, pnl_cube)
    # setup cubes: Sales, HR, CurConv

    return db


def populate_cube_pnl(db: Database, pnl: Cube):
    """Populate the Profit & Loss cube"""
    # Now it will now a bit tricky as we want to create somehow realistic figures
    pnl_dim = db.dimensions.get("pnl")
    companies = db.get_dimension("companies").get_leave_members()
    years = db.get_dimension("years").get_leave_members()  # Jan... Dec
    months = db.get_dimension("periods").get_leave_members()  # Jan... Dec
    dim_positions = db.get_dimension("pnl")
    positions = dim_positions.get_leave_members()  # all non aggregated P&L positions
    seasonality = [1.329471127, 0.997570548, 0.864137544, 0.987852738, 0.770697066, 0.791253971,
                   1.141095122, 0.83984302, 0.932909736, 1.158661932, 1.113810503, 1.072696692]
    z = 0
    for company in companies:
        trend_factor = random.gauss(.02, 0.02)  # annual trend for each company's sales, avg := 10% increase
        baseline_factor = max(1.0, random.gammavariate(2, 2))  # multiplier (growth) for all P&L figures
        monthly_factors = [m + random.gauss(0, 0.05) for m in seasonality]  # add some noise to the seasonality
        # print(f"{company} has trend :={trend}, baseline := {sales_baseline_factor}")
        for year in years:
            for month, monthly_factor in zip(months, monthly_factors):
                factor = (1 + trend_factor) * baseline_factor * monthly_factor
                for position in positions:
                    factor = factor + random.gauss(0, factor * 0.05)  # add some noise on the P&L figures
                    sample = dim_positions.get_attribute("sample", position)
                    actual = round(sample * factor, ndigits=0)
                    plan = round(random.gauss(actual * 1.05, actual * 0.05),
                                 ndigits=int(-(math.log10(abs(actual)) - 1.0)))
                    forecast = round(random.gauss(actual * 1.1, actual * 0.15),
                                     ndigits=int(-(math.log10(abs(actual)) - 1.0)))

                    # write value to cube
                    pnl["Actual", year, month, company, position] = actual
                    pnl["Plan", year, month, company, position] = plan
                    pnl["Forecast", year, month, company, position] = forecast
                    # print(f"{z} [{year}, {month}, {company}, {position}>>> ACT = {actual}, PL = {plan}, FC = {forecast}")
                    z = z + 1
                # increase the monthly trend factor
                trend_factor = trend_factor + random.gauss(0.01, 0.01)
    print(f"number of cells is {z}")


# region Dimension Creation
def add_dimension_periods(db: Database, name: str = "periods") -> Dimension:
    """
    Dimension defining the periods of the year: months, quarters half-years and year
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """

    dim = db.add_dimension(name).edit()
    dim.add_member(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    dim.add_member(["Q1", "Q2", "Q3", "Q4"],
                   [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                    ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
    dim.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
    dim.add_member(["HY1", "HY2"], [("Jan", "Feb", "Mar", "Apr", "Mai", "Jun"),
                                    ("Jul", "Aug", "Sep", "Oct", "Nov", "Dec")])
    dim.commit()

    # Attributes
    dim.add_attribute("longname", str)
    # first copy the member name as the default long name.
    for member in dim.get_members():
        dim.set_attribute("longname", member, member)
    # set proper long names for months
    for pair in (("Jan", "January"), ("Feb", "February"), ("Mar", "March"),
                 ("Apr", "April"), ("Mai", "Mai"), ("Jun", "June"),
                 ("Jul", "July"), ("Aug", "August"), ("Sep", "September"),
                 ("Oct", "October"), ("Nov", "November"), ("Dec", "December")):
        dim.set_attribute("longname", pair[0], pair[1])

    return dim


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
      Forecast := Forecast figures
      DevPlan, DevFC := Deviation of actual vs forecast (rules required)
      DevPlan%, DevFC% := Deviation of actual vs forecast in percent (rules required)
      DevPY := Delta previous year (rule required)
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    d.add_member(["Actual", "Plan", "Forecast",
                  "ACTvsPL", "ACTvsPL%",
                  "ACTvsFC", "ACTvsFC%",
                  "ACTvsACTpy", "ACTvsACTpy%",
                  "FCvsPL", "FCvsPL%",
                  "FCvsACTpy", "FCvsACTpy%"])
    d.commit()
    for member in ["Actual", "Plan", "Forecast"]:
        d.member_set_format(member, "{:,.0f}")  # set default number format
    for member in ["ACTvsPL", "ACTvsFC", "ACTvsACTpy", "FCvsPL", "FCvsACTpy"]:
        d.member_set_format(member, "{:+,.0f}")  # set default number format
    for member in ["ACTvsPL%", "ACTvsFC%", "ACTvsACTpy%", "FCvsPL%", "FCvsACTpy%"]:
        d.member_set_format(member, "{:+.2%}")  # number format for percentages
    return d


def add_dimension_pnl_statement(db: Database, name: str = "pnl") -> Dimension:
    """
    Dimension defining the chart of account for a profit & loss statement:
    The chart of account and the required calcuation logic are maintained in a speparate file.
    Will also dynamically create rule from that file. Better than to type all the rules by hand.

    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    dim = db.add_dimension(name).edit()

    # Revenue
    dim.add_member(["Gross Sales",
                    "Sales Returns",
                    "Discounts and Allowances"])
    dim.add_member("Net Sales", ["Gross Sales", "Sales returns", "Discounts and Allowances"])
    # Cost of Goods Sold
    dim.add_member(["Raw Materials",
                    "Direct Labor",
                    "Overheads"])
    dim.add_member("Cost of Goods Sold", ["Raw Materials", "Direct Labor", "Overheads"])
    # Gross Profit
    dim.add_member("Gross Profit", ["Net Sales", "Cost of Goods Sold"])
    # Operating Expenses
    dim.add_member("Operating Expenses",
                   ["Advertising",
                    "Delivery/Freight",
                    "Depriciation",
                    "Insurance",
                    "Office Supplies",
                    "Rent/Lease",
                    "Maintenance and Repairs",
                    "Travel",
                    "Wages",
                    "Utilities",
                    "Other Expenses"])

    dim.add_member("Operating Profit", ["Gross Profit", "Operating Expenses"])
    dim.add_member("Profit Before Taxes", ["Operating Profit", "Interest Income", "Other Income"])
    dim.add_member("Net Profit", ["Profit Before Taxes", "Tax Expense"])
    dim.commit()

    # Attributes
    # we add an attribute that contains realistic sample value
    # for the various P&L positions. These will be used for sample data generation.
    dim.add_attribute("sample", float)
    for pair in (("Gross Sales", 78000.0),
                 ("Sales Returns", -3200.0),
                 ("Discounts and Allowances", -1000.0),
                 ("Raw Materials", -8100.0),
                 ("Direct Labor", -10000.0),
                 ("Overheads", -2100.0),
                 ("Advertising", -600.0),
                 ("Delivery/Freight", -1500.0),
                 ("Depriciation", -8000.0),
                 ("Insurance", -550.0),
                 ("Office Supplies", 1300.0),
                 ("Rent/Lease", -5800.0),
                 ("Maintenance and Repairs", -200.0),
                 ("Travel", -200.0),
                 ("Wages", 10000.0),
                 ("Utilities", -800.0),
                 ("Other Expenses", -230.0),
                 ("Interest Income", 1700.0),
                 ("Other Income", 1250.0),
                 ("Tax Expense", -10000.0)):
        dim.set_attribute("sample", pair[0], pair[1])

    # Subsets
    dim.add_subset("Expenses",
                   ["Advertising",
                    "Delivery/Freight",
                    "Depriciation",
                    "Insurance",
                    "Office Supplies",
                    "Rent/Lease",
                    "Maintenance and Repairs",
                    "Travel",
                    "Wages",
                    "Utilities",
                    "Other Expenses"])

    dim.add_subset("Overview",
                   ["Gross Sales",
                    "Net Sales",
                    "Gross Profit",
                    "Operating Expenses",
                    "Operating Profit",
                    "Profit Before Taxes",
                    "Net Profit"])

    return dim


def add_dimension_company(db: Database, name: str = "companies", group_name: str = "Tiny Corp.",
                          companies_count: int = 20, international: bool = True) -> Dimension:
    """
    Creates a random company dimension, with defined parameters.
    :param db: The target database.
    :param name: Name of the dimension
    :param group_name: Name of the topmost group company.
    :param companies_count: Number of legal entities to create.
    :param international: If true a hierarchy of countries and regions will be added.
    :return: The new dimension.
    """
    Faker.seed(0)
    fake = Faker()

    # create company dimension
    dim = db.add_dimension(name).edit()
    if not international:
        dim.add_member(group_name, [fake.company() for i in range(companies_count)])
    else:
        dim.add_member(group_name, ["EMEA", "NA", "LATAM", "APAC"])
        companies_per_region = int(companies_count / 4)
        for region in ["EMEA", "NA", "LATAM", "APAC"]:
            dim.add_member(region, [fake.company() for i in range(companies_per_region)])
    dim.commit()

    # Attributes
    dim.add_attribute("manager", str)
    for member in dim.get_members():
        dim.set_attribute("manager", member, fake.name())

    return dim


# endregion

# region Rules
@rule("pnl", ["ACTvsPL"])
def rule_datatype_actvspl(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Plan."""
    return c["Actual"] - c["Plan"]


@rule("pnl", ["ACTvsPL%"])
def rule_datatype_actvspl_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Plan in %."""
    plan = c["Plan"]
    if plan:
        return (c["Actual"] - plan) / plan
    return None


@rule("pnl", ["ACTvsFC"])
def rule_datatype_actvsfc(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Forecast."""
    return c["Actual"] - c["Forecast"]


@rule("pnl", ["ACTvsFC%"])
def rule_datatype_actvsfc_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Forecast in %."""
    fc = c["Forecast"]
    if fc:
        return (c["Actual"] - fc) / fc
    return None


@rule("pnl", ["FCvsPL"])
def rule_datatype_fcvspl(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Plan."""
    return c["Forecast"] - c["Plan"]


@rule("pnl", ["FCvsPL%"])
def rule_datatype_fcvspl_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Plan in %."""
    plan = c["Plan"]
    if plan:
        return (c["Forecast"] - plan) / plan
    return None


@rule("pnl", ["FCvsACTpy"])
def rule_datatype_fcvsactpy(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Actual Previous Year."""
    prev_year = c.member("years").previous()
    if prev_year:
        return c["Forecast"] - c[prev_year, "Actual"]
    return None


@rule("pnl", ["FCvsACTpy%"])
def rule_datatype_fcvsactpy_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Actual Previous Year in %."""
    prev_year = c.member("years").previous()
    if prev_year:
        actual = c[prev_year, "Actual"]
        if actual:
            return (c["Forecast"] - actual) / actual
        return None
    return None


@rule("pnl", ["ACTvsACTpy"])
def rule_datatype_actvactpy(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Actual Previous Year."""
    prev_year = c.member("years").previous()
    if prev_year:
        return c["Actual"] - c[prev_year, "Actual"]
    return None


@rule("pnl", ["ACTvsACTpy%"])
def rule_datatype_actvactpy_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Actual Previous Year in %."""
    prev_year = c.member("years").previous()
    if prev_year:
        actual = c[prev_year, "Actual"]
        if actual:
            return (c["Actual"] - actual) / actual
        return None
    return None


@rule("sales", ["Profit in %"], scope=RuleScope.ALL_LEVELS, volatile=False)
def rule_profit_in_percent(c: Cell):
    """Rule to calculate the Profit in %."""
    sales = c["Sales"]
    profit = c["Profit"]
    if sales:
        return profit / sales
    return None

# endregion
