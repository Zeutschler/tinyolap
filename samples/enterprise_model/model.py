# Purpose: Creation of the Enterprise sample database.
from __future__ import annotations
import datetime
import itertools
import math
import os.path

import random
import time
import timeit

from faker import Faker
from faker.providers import bank

from tinyolap.dimension import Dimension
from tinyolap.decorators import rule
from tinyolap.database import Database
from tinyolap.database import Cube
from tinyolap.rules import RuleScope, RuleInjectionStrategy
from tinyolap.area import Area
from tinyolap.cell import Cell
from tinyolap.slice import Slice


def create_database(name: str = "enterprise", database_directory: str = None,
                    num_legal_entities: int = 50, num_products: int = 100,
                    num_employees: int = 500, console_output: bool = True):
    """
    Creates a new Enterprise sample database instance.
    :param name: The name of the database.
    :param database_directory: The file location for the database. If not provided, an in-memory data will be created.
    :param num_legal_entities: : Defines the number of legal entities the enterprise should have.
    :param num_products: : Defines the number of legal products the enterprise should have.
    :param num_employees: : Defines the number of employees the enterprise should have.
    :param console_output: Identifies id console output is allowed.
    :return: The created enterprise database.
    """

    # set up the database
    if console_output:
        print(f"Creating database '{name}' with {num_legal_entities} legal entities, "
              f"{num_products} products "
              f"and {num_employees} employees. Please wait...")
    if not database_directory:
        db = Database(name=name, in_memory=True)
    else:
        db = Database(name=os.path.join(database_directory, name, ".db"))

    # setup all dimensions
    if console_output:
        print(f"\tCreating dimension...")
    datatype = add_dimension_datatype(db)
    years = add_dimension_years(db)
    periods = add_dimension_periods(db)
    company = add_dimension_company(db, companies_count=num_legal_entities)
    pnl = add_dimension_pnl_statement(db)

    products = add_dimension_products(db, products_count=num_products)
    salesfig = add_dimension_sales_figures(db)

    employees = add_dimension_employees(db, company_dim_name=company.name, employees_count=num_employees)
    hrfig = add_dimension_hr_figures(db)

    if console_output:
        print(f"\t\tDone!")

    # cube 'PnL'
    pnl_cube = db.add_cube("pnl", [datatype, years, periods, company, pnl])
    if console_output:
        print(f"\tGenerating data for cube '{pnl_cube.name}'. This may take a while...")
    for func in [rule_datatype_actvspl, rule_datatype_actvspl_percent,
                       rule_datatype_actvsfc, rule_datatype_actvsfc_percent,
                       rule_datatype_fcvspl, rule_datatype_fcvspl_percent,
                       rule_datatype_fcvsactpy, rule_datatype_fcvsactpy_percent,
                       rule_datatype_actvactpy, rule_datatype_actvactpy_percent]:
        pnl_cube.register_rule(func)
    populate_cube_pnl(db, pnl_cube)
    if console_output:
        print(f"\t\tDone! Cube '{pnl_cube.name}' contains {pnl_cube.cells_count:,} cells")

    # setup cubes: Sales
    sales_cube = db.add_cube("sales", [years, periods, company, products, salesfig])
    if console_output:
        print(f"\tGenerating data for cube '{sales_cube.name}'. This may take a while...")
    for func in [rule_sales_price]:
        sales_cube.register_rule(func)
    populate_cube_sales(db, sales_cube)
    if console_output:
        print(f"\t\tDone! Cube '{sales_cube.name}' contains {sales_cube.cells_count:,} cells")

    # setup cube: HR
    hr_cube = db.add_cube("hr", [years, employees, hrfig])
    if console_output:
        print(f"\tGenerating data for cube '{hr_cube.name}'. This may take a while...")
    populate_cube_hr(db, hr_cube)
    if console_output:
        print(f"\t\tDone! Cube '{hr_cube.name}' contains {hr_cube.cells_count:,} cells")

    if console_output:
        print(f"All Done! Database '{db.name}' is now read for use.")
    return db


# region Cube Population
def populate_cube_pnl(db: Database, cube: Cube):
    """Populate the Profit & Loss cube"""
    # This will get a bit weird / tricky as we want to create somehow realistic figures
    companies = db.get_dimension("companies").get_leaves()
    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    months = db.get_dimension("periods").get_leaves()  # Jan... Dec
    dim_positions = db.get_dimension("pnl")
    positions = dim_positions.get_leaves()  # all non aggregated P&L positions
    seasonality = [1.329471127, 0.997570548, 0.864137544, 0.987852738, 0.770697066, 0.791253971,
                   1.141095122, 0.83984302, 0.932909736, 1.158661932, 1.113810503, 1.072696692]
    z = 0
    for company in companies:
        trend_factor = random.gauss(.02, 0.02)  # annual trend for each company's sales, avg := 10% increase
        baseline_factor = max(1.0, random.gammavariate(2, 2))  # multiplier (growth) for all P&L figures
        monthly_factors = [m + random.gauss(0, 0.05) for m in seasonality]  # add some noise to the seasonality
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
                    # write values to cube
                    cube["Actual", year, month, company, position] = actual
                    cube["Plan", year, month, company, position] = plan
                    cube["Forecast", year, month, company, position] = forecast
                    z = z + 1
                # increase the monthly trend factor
                trend_factor = trend_factor + random.gauss(0.01, 0.01)


def populate_cube_sales(db: Database, cube: Cube):
    """Populate the Sales cube"""
    # The basic idea is that not all companies sell all products, but only a few (as in real life)

    companies = db.get_dimension("companies").get_leaves()
    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    months = db.get_dimension("periods").get_leaves()  # Jan... Dec
    product_dim = db.get_dimension("products")
    products = product_dim.get_leaves()  # all non aggregated P&L positions
    seasonality = [1.329471127, 0.997570548, 0.864137544, 0.987852738, 0.770697066, 0.791253971,
                   1.141095122, 0.83984302, 0.932909736, 1.158661932, 1.113810503, 1.072696692]
    z = 0
    for company in companies:
        for product in products:
            if random.random() > 0.50:  # companies only sell 20% of the existing products
                continue
            starting_year = int(random.choice(years[:-min(-1, len(years)-4)]))
            starting_month = random.choice(months)
            yearly_price_increase = 1.0
            for year in years:
                if int(year) < starting_year:
                    continue
                for month in months:
                    if starting_month:
                        if month != starting_month:
                            continue
                        starting_month = False
                    quantity = abs(int(random.gammavariate(2, 2)*4))
                    if quantity > 0:
                        price = product_dim.get_attribute("list_price", product)
                        price = round(price * yearly_price_increase, -1) - 1
                        cube[year, month, company, product, "Quantity"] = quantity
                        cube[year, month, company, product, "Sales"] = quantity * price
                        z = z + 2
                yearly_price_increase += (0.01 + random.random() * 0.04)


def populate_cube_hr(db: Database, cube: Cube):
    """Populate the HR cube"""
    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    hr_dim = db.get_dimension("employees")
    employees = hr_dim.get_leaves()  # all non aggregated P&L positions
    z = 0
    root_salary = 100000.0
    for employee in employees:
        yearly_salary_increase = 1.0
        salary = max(30000.0, round(root_salary * random.gauss(1.0, 0.2), -4))
        for year in years:
            salary = round(salary * yearly_salary_increase, -4)
            cube[year, employee, "Base Salary"] = salary
            cube[year, employee, "Bonus"] = round(random.uniform(0.0, 50000.0), -4)
            claim = 30.0 if random.random() < 0.8 else 25.0
            cube[year, employee, "Holiday claim"] = 30 if random.random() < 0.8 else 25
            cube[year, employee, "Holidays taken"] = claim - float(random.randrange(0, 5, 1))
    return cube
# endregion


# region Dimension Creation
def add_dimension_periods(db: Database, name: str = "periods") -> Dimension:
    """
    Dimension defining the periods of the year: months, quarters half-years and year
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """

    dim = db.add_dimension(name).edit()
    dim.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
    dim.add_member(["Q1", "Q2", "Q3", "Q4"],
                   [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                    ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
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
    # we add an attribute that contains somehow realistic sample values
    # for our P&L figures. These will be used later to generate randomized data.
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
                          companies_count: int = 25, international: bool = True) -> Dimension:
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


def add_dimension_products(db: Database, name: str = "products", products_count: int = 100) -> Dimension:
    """
    Creates a random company dimension, with defined parameters.
    :param db: The target database.
    :param name: Name of the dimension
    :param products_count: Number of legal entities to create.
    :return: The new dimension.
    """
    Faker.seed(0)
    fake = Faker()
    fake.add_provider(bank)

    families = ['OLAP', 'MOLAP', 'HOLAP', 'ROLAP', 'AI/OLAP']
    lines = ['Access Database', 'Acumen Database', 'Agile OLAP', 'Agile OLAP', 'Algorithm Database',
                'Alpha Database', 'App OLAP', 'Artificial Database', 'Artificial OLAP', 'Binary Database',
                'Bit Database', 'Bot OLAP', 'Byte Database', 'Byte OLAP', 'Check OLAP', 'Condition Database',
                'Condition OLAP', 'Core OLAP', 'Cyber Database', 'Cyper OLAP', 'Data OLAP', 'Databaseadil',
                'Databasebia', 'Databaseegy', 'Databaseex', 'Databaseiva', 'Databaselia', 'Databasely',
                'Databaselytical', 'Databaseopolis', 'Databaseporium', 'Databasesio', 'Databasester', 'Databasetastic',
                'Desk Database', 'Dev Database', 'Dock OLAP', 'Edge Database', 'Electric OLAP', 'Elevate OLAP',
                'Enigma Database', 'Expression OLAP', 'Fiber Database', 'Flash Database', 'Fuel Database',
                'Fusion Database', 'Giga OLAP', 'Hack OLAP', 'Hover Database', 'Hover OLAP', 'Hyper Database',
                'Illuminate Database', 'Illuminate OLAP', 'Infinity OLAP', 'Insight Database', 'Intellect Database',
                'Intuition Database', 'Level OLAP', 'Link Database', 'Lock OLAP', 'Macro Database', 'Mega OLAP',
                'Micro OLAP', 'Mobile OLAP', 'Modular Database', 'Modular OLAP', 'Nest OLAP', 'Net OLAP',
                'Network OLAP', 'OLAPadil', 'OLAPjet', 'OLAPlia', 'OLAPocity', 'OLAPomatic', 'OLAPscape', 'OLAPya',
                'Operator Database', 'Operator OLAP', 'Optimal OLAP', 'Optimize OLAP', 'Path OLAP', 'Pivot OLAP',
                'Pixel Database', 'Rank Database', 'Rank OLAP', 'Rubicon Database', 'Rubicon OLAP', 'Script OLAP',
                'Sign Database', 'Smart OLAP', 'Soft OLAP', 'Soft OLAP', 'Solar Database', 'Solar OLAP', 'Spire OLAP',
                'Sprint Database', 'Synthetic OLAP', 'Task OLAP', 'Veritas Database',
                'Vision Database']
    editions = ['Free Edition' ,'Professional Edition', 'Enterprise Edition', 'Developer Edition', 'Education Edition']
    packs = ['Single User Pack', '5-User Pack', '10-User Pack', '50-User Pack', '100-User Pack', '1000-User Pack', 'Enterprise Licence']

    dim = db.add_dimension(name).edit()
    products = []

    z = 0
    family_factor = float(len(families)) / float(products_count) * 10
    line_factor = float(len(lines)) / float(products_count)
    remaining_lines = list(lines)
    for i in range(products_count):
        family = random.choice(families)
        line = random.choice(remaining_lines)
        remaining_lines.remove(line)
        if len(remaining_lines) == 0:
            break

        dim.add_member("All Products", family)
        dim.add_member(family, line)

        # select some editions
        min = random.randrange(0, len(editions) - 1)
        max = random.randrange(0, len(editions) - 1)
        if min > max:
            min, max = max, min
        for edition in editions[min:max + 1]:
            # select some packs
            min = random.randrange(0, len(packs) - 1)
            max = random.randrange(0, len(packs) - 1)
            if min > max:
                min, max = max, min
            for pack in packs[min:max + 1]:
                product = line + ", " + edition + " (" + pack + ")"
                dim.add_member(line, product)
                products.append(product)

                z = z + 1
                if z >= products_count:
                    break
            if z >= products_count:
                break
        if z >= products_count:
            break
    dim.commit()

    # Attributes
    dim.add_attribute("color", str)
    dim.add_attribute("id", str)
    dim.add_attribute("list_price", float)
    for member in products:
        dim.set_attribute("color", member, fake.color())
        dim.set_attribute("id", member, fake.unique.bothify(text='Product Number: ????-########'))
        dim.set_attribute("list_price", member, float(50 + int(random.random() * 20.0) * 50 - 1))

    return dim


def add_dimension_sales_figures(db: Database, name: str = "salesfig") -> Dimension:
    """
    Dimension defining sales figures
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    d.add_member(["Sales", "Quantity", "Price"])
    d.commit()
    for member in ["Sales", "Quantity"]:
        d.member_set_format(member, "{:,.0f}")
    for member in ["Price"]:
        d.member_set_format(member, "{:.2f}")
    return d


def add_dimension_employees(db: Database, company_dim_name: str = "companies", name: str = "employees",
                          employees_count: int = 200) -> Dimension:
    """
    Creates a random employee dimension.
    :param company_dim_name: Name of the company dimension
    :param db: The target database.
    :param name: Name of the dimension
    :param employees_count: Number of employees to create.
    :return: The new dimension.
    """
    Faker.seed(0)
    fake = Faker()

    # get company dimension to reuse its hierarchy
    company_dim = db.get_dimension(company_dim_name)


    # create employee dimension
    dim = db.add_dimension(name).edit()
    companies = company_dim.get_leaves()
    employees_per_company = max(1, int(employees_count / len(companies)))
    for company in companies:
        # copy the member hierarchy from the company dimension first
        hierarchy = [company, ]
        parents = company_dim.member_get_parents(company)
        while parents:
            hierarchy.append(parents[0])
            parents = company_dim.member_get_parents(parents[0])
        for i in range(len(hierarchy)-1, 0, -1):
            dim.add_member(hierarchy[i], [hierarchy[i-1]])
        # now add employees
        dim.add_member(company, [fake.name() for i in range(employees_per_company)])
    dim.commit()

    # Attributes
    # dim.add_attribute("manager", str)
    # for member in dim.get_members():
    #     dim.set_attribute("manager", member, fake.name())
    return dim

def add_dimension_hr_figures(db: Database, name: str = "hrfig") -> Dimension:
    """
    Dimension defining HR figures
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    d.add_member(["Base Salary", "Bonus", "Holiday claim", "Holidays taken"])
    d.commit()
    for member in ["Holiday claim", "Holidays taken"]:
        d.member_set_format(member, "{:,.0f}")
    for member in ["Base Salary", "Bonus",]:
        d.member_set_format(member, "{:,.0f}")
    return d
# endregion


# region Rules for Sales
@rule("sales", ["Price"])
def rule_sales_price(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    quantity = c["salesfig:Quantity"]
    if quantity:
        return c["salesfig:Sales"] / quantity
    return None
# endregion

# region Rules for P&L statement
@rule("pnl", ["ACTvsPL"])
def rule_datatype_actvspl(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Plan."""
    return c["datatype:Actual"] - c["datatype:Plan"]


@rule("pnl", ["ACTvsPL%"])
def rule_datatype_actvspl_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Plan in %."""
    plan = c["datatype:Plan"]
    if plan:
        return (c["datatype:Actual"] - plan) / plan
    return None


@rule("pnl", ["ACTvsFC"])
def rule_datatype_actvsfc(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Forecast."""
    return c["datatype:Actual"] - c["datatype:Forecast"]


@rule("pnl", ["ACTvsFC%"])
def rule_datatype_actvsfc_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Forecast in %."""
    fc = c["datatype:Forecast"]
    if fc:
        return (c["datatype:Actual"] - fc) / fc
    return None


@rule("pnl", ["FCvsPL"])
def rule_datatype_fcvspl(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Plan."""
    return c["datatype:Forecast"] - c["datatype:Plan"]


@rule("pnl", ["FCvsPL%"])
def rule_datatype_fcvspl_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Plan in %."""
    plan = c["datatype:Plan"]
    if plan:
        return (c["datatype:Forecast"] - plan) / plan
    return None


@rule("pnl", ["FCvsACTpy"])
def rule_datatype_fcvsactpy(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Actual Previous Year."""
    prev_year = c.member("years").previous()
    if prev_year:
        return c["datatype:Forecast"] - c["years:" + str(prev_year), "datatype:Actual"]
    return None


@rule("pnl", ["FCvsACTpy%"])
def rule_datatype_fcvsactpy_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Actual Previous Year in %."""
    prev_year = c.member("years").previous()
    if prev_year:
        actual = c["years:" + str(prev_year), "datatype:Actual"]
        if actual:
            return (c["datatype:Forecast"] - actual) / actual
        return None
    return None


@rule("pnl", ["ACTvsACTpy"])
def rule_datatype_actvactpy(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Actual Previous Year."""
    prev_year = c.member("years").previous()
    if prev_year:
        return c["datatype:Actual"] - c["years:" + str(prev_year), "datatype:Actual"]
    return None


@rule("pnl", ["ACTvsACTpy%"])
def rule_datatype_actvactpy_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Actual Previous Year in %."""
    prev_year = c.member("years").previous()
    if prev_year:
        actual = c["years:" + str(prev_year), "datatype:Actual"]
        if actual:
            return (c["datatype:Actual"] - actual) / actual
        return None
    return None




# endregion


if __name__ == "__main__":
    # Playtime!!! ʕ•́ᴥ•̀ʔっ
    db = create_database()
