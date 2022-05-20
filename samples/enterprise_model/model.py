# Purpose: Creation of the Enterprise sample database.
from __future__ import annotations
import datetime
import itertools
import math
import os.path

import random
import time
import timeit

from samples.enterprise_model import entities
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
from halo import Halo


def create_database(name: str = "enterprise", database_directory: str = None,
                    num_legal_entities: int = 50, num_products: int = 100,
                    num_employees: int = 500, console_output: bool = True,
                    caching=False, callback= None):
    """
    Creates a new Enterprise sample database instance.
    :param name: The name of the database.
    :param database_directory: The file location for the database. If not provided, an in-memory data will be created.
    :param num_legal_entities: : Defines the number of legal entities the enterprise should have.
    :param num_products: : Defines the number of legal products the enterprise should have.
    :param num_employees: : Defines the number of employees the enterprise should have.
    :param console_output: Identifies id console output is allowed.
    :param caching: Defines is caching should be used.
    :param callback: Callback function to report on progress.
           Callback function signature: func(progress: int, message: str)
    :return: The created enterprise database.
    """

    spinner = None
    if console_output:
        spinner = Halo(text=f"Creating database '{name}", spinner="dots")
        spinner.start()
    if callback:
        callback(0, f"Creating data model for database '{name}.")

    # set up the database
    if not database_directory:
        db = Database(name=name, in_memory=True)
    else:
        db = Database(name=os.path.join(database_directory, name, ".db"))
    db.description = f"Planning & reporting of {name}"

    # set up dimensions
    datatype = add_dimension_datatype(db)
    if callback:
        callback(1, f"Dimension '{datatype.name} with {len(datatype.members)} members added.")

    years = add_dimension_years(db)
    if callback:
        callback(2, f"Dimension '{years.name} with {len(years.members)} members added")

    periods = add_dimension_periods(db)
    if callback:
        callback(3, f"Dimension '{periods.name} with {len(periods.members)} members added")

    countries = add_dimension_countries(db, countries_count=(num_legal_entities // 4))
    if callback:
        callback(4, f"Dimension '{countries.name} with {len(countries.members)} members added")

    curcodes = add_dimension_curcodes(db)
    if callback:
        callback(4, f"Dimension '{curcodes.name} with {len(curcodes.members)} members added")

    currency = add_dimension_currency(db)
    if callback:
        callback(4, f"Dimension '{currency.name} with {len(currency.members)} members added")

    company = add_dimension_company(db, companies_count=num_legal_entities)
    if callback:
        callback(4, f"Dimension '{company.name} with {len(company.members)} members added")

    pnl = add_dimension_pnl_statement(db)
    if callback:
        callback(5, f"Dimension '{pnl.name} with {len(pnl.members)} members added")

    products = add_dimension_products(db, products_count=num_products)
    if callback:
        callback(6, f"Dimension '{products.name} with {len(products.members)} members added")

    salesfig = add_dimension_sales_figures(db)
    if callback:
        callback(7, f"Dimension '{salesfig.name} with {len(salesfig.members)} members added")

    employees = add_dimension_employees(db, company_dim_name=company.name, employees_count=num_employees)
    if callback:
        callback(8, f"Dimension '{employees.name} with {len(employees.members)} members added")

    hrfig = add_dimension_hr_figures(db)
    if callback:
        callback(9, f"Dimension '{hrfig.name} with {len(hrfig.members)} members added")

    # cube 'exrates'
    exrates_cube = db.add_cube("exrates", [datatype, years, periods, curcodes])
    populate_cube_exrates(db, exrates_cube, spinner, callback, 10, 14)

    # cube 'PnL'
    pnl_cube = db.add_cube("pnl", [datatype, years, periods, company, pnl])
    pnl_cube.description = f"Profit & loss statements of {name}"
    for func in [rule_datatype_actvspl_percent, rule_datatype_actvsfc_percent,
                       rule_datatype_fcvspl_percent,
                       rule_datatype_fcvsactpy, rule_datatype_fcvsactpy_percent,
                       rule_datatype_actvactpy, rule_datatype_actvactpy_percent]:
        pnl_cube.register_rule(func)
    populate_cube_pnl(db, pnl_cube, spinner, callback, 15, 40)
    if callback:
        callback(50, f"Cube '{pnl_cube.name} with {pnl_cube.dimensions_count} dimensions added.")

    # cube 'PnL' with currency conversion
    pnl_lcgc_cube = db.add_cube("pnl_lcgc", [currency, datatype, years, periods, company, pnl])
    pnl_lcgc_cube.description = f"Profit & loss statements of {name} with LC/GC"
    for func in [rule_datatype_actvspl_percent, rule_datatype_actvsfc_percent,
                       rule_datatype_fcvspl_percent,
                       rule_datatype_fcvsactpy, rule_datatype_fcvsactpy_percent,
                       rule_datatype_actvactpy, rule_datatype_actvactpy_percent,
                       rule_lc_to_gc
                ]:
        pnl_lcgc_cube.register_rule(func)
    populate_cube_pnl(db, pnl_lcgc_cube, spinner, callback, 15, 40)
    if callback:
        callback(50, f"Cube '{pnl_lcgc_cube.name} with {pnl_lcgc_cube.dimensions_count} dimensions added.")

    # setup cubes: Sales
    sales_cube = db.add_cube("sales", [years, periods, company, products, salesfig])
    sales_cube.description = f"Product sales of {name}"
    for func in [rule_sales_price]:
        sales_cube.register_rule(func)
    populate_cube_sales(db, sales_cube, spinner, callback, 50, 40)
    if callback:
        callback(90, f"Cube '{pnl_cube.name} with {pnl_cube.dimensions_count} dimensions added.")

    # setup cube: HR
    hr_cube = db.add_cube("hr", [years, employees, hrfig])
    hr_cube.description = f"Salary data per employee of {name}"
    populate_cube_hr(db, hr_cube, spinner, callback, 90, 10)
    if callback:
        callback(100, f"Cube '{pnl_cube.name} with {pnl_cube.dimensions_count} dimensions added.")

    if console_output:
        spinner.stop()

    db.caching = caching
    if callback:
        callback(100, f"Database '{db.name} successfully created.")
    return db


def populate_cube_exrates(db: Database, cube: Cube, spinner, callback=None, progress_start=0, progress_width=0):
    """Populate the Profit & Loss cube"""
    if spinner:
        spinner.text = f"Generating data for '{db.name}:{cube.name} "


    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    months = db.get_dimension("periods").get_leaves()  # Jan... Dec
    datatype = ["Actual", "Plan", "Forecast"]
    curcodes = db.get_dimension("curcodes").get_leaves()

    z = 0
    for idx, curcode in enumerate(curcodes):
        base_value = max(0.1, random.gauss(1, 0.5))
        for datatype, base_value in zip(["Actual", "Plan", "Forecast"], [base_value, base_value * 1.04, base_value, 1.02]):
            s = random.random()
            for year, month in itertools.product(years, months):
                exrate = base_value + (math.sin(s) + 1.0) / 2.0 * base_value / 10.0
                s += math.pi / 12
                cube[datatype, year, month, curcode] = exrate
                z = z + 1
        if spinner:
            spinner.text = f"Generating data for '{db.name}:{cube.name}' ({z:,} records) -> {curcode}"
        if callback:
            callback(progress_start + progress_width * idx // len(curcode),
                     f"Generating data for cube '{db.name}:{cube.name}' ({z:,} records) -> {curcode}")


# region Cube Population
def populate_cube_pnl(db: Database, cube: Cube, spinner, callback=None, progress_start=0, progress_width=0):
    """Populate the Profit & Loss cube"""
    if spinner:
        spinner.text = f"Generating data for '{db.name}:{cube.name} "

    # This will get a bit weird / tricky as we want to create somehow realistic figures
    with_currency = cube.dimensions_count == 6
    companies = db.get_dimension("companies").get_leaves()
    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    months = db.get_dimension("periods").get_leaves()  # Jan... Dec
    dim_positions = db.get_dimension("pnl")
    positions = dim_positions.get_leaves()  # all non aggregated P&L positions
    seasonality = [1.329471127, 0.997570548, 0.864137544, 0.987852738, 0.770697066, 0.791253971,
                   1.141095122, 0.83984302, 0.932909736, 1.158661932, 1.113810503, 1.072696692]
    z = 0
    for idx, company in enumerate(companies):
        trend_factor = random.gauss(.02, 0.02)  # annual trend for each company's sales, avg := 10% increase
        baseline_factor = max(1.0, random.gammavariate(2, 2))  # multiplier (growth) for all P&L figures
        monthly_factors = [m + random.gauss(0, 0.05) for m in seasonality]  # add some noise to the seasonality
        for year in years:
            for month, monthly_factor in zip(months, monthly_factors):
                factor = (1 + trend_factor) * baseline_factor * monthly_factor
                for position in positions:
                    factor = factor + random.gauss(0, factor * 0.05)  # add some noise on the P&L figures
                    sample = dim_positions.attributes["sample"][position]
                    # sample = dim_positions.get_attribute("sample", position)
                    actual = round(sample * factor, ndigits=0)
                    plan = round(random.gauss(actual * 1.05, actual * 0.05),
                                 ndigits=int(-(math.log10(abs(actual)) - 1.0)))
                    forecast = round(random.gauss(actual * 1.1, actual * 0.15),
                                     ndigits=int(-(math.log10(abs(actual)) - 1.0)))
                    # write values to cube
                    if with_currency:
                        cube["LC", "Actual", year, month, company, position] = actual
                        cube["LC", "Plan", year, month, company, position] = plan
                        cube["LC", "Forecast", year, month, company, position] = forecast
                    else:
                        cube["Actual", year, month, company, position] = actual
                        cube["Plan", year, month, company, position] = plan
                        cube["Forecast", year, month, company, position] = forecast
                    z = z + 3

                # increase the monthly trend factor
                trend_factor = trend_factor + random.gauss(0.01, 0.01)

        if spinner:
            spinner.text = f"Generating data for '{db.name}:{cube.name}' ({z:,} records) -> {company}"
        if callback:
            callback(progress_start + progress_width * idx // len(companies),
                     f"Generating data for cube '{db.name}:{cube.name}' ({z:,} records) -> {company}")

def populate_cube_sales(db: Database, cube: Cube, spinner, callback= None, progress_start=0, progress_width=0):
    """Populate the Sales cube"""
    # The basic idea is that not all companies sell all products, but only a few (as in real life)

    if spinner:
        spinner.text = f"Generating data for '{db.name}:{cube.name}: "

    companies = db.get_dimension("companies").get_leaves()
    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    months = db.get_dimension("periods").get_leaves()  # Jan... Dec
    product_dim = db.get_dimension("products")
    products = product_dim.get_leaves()  # all non aggregated P&L positions
    seasonality = [1.329471127, 0.997570548, 0.864137544, 0.987852738, 0.770697066, 0.791253971,
                   1.141095122, 0.83984302, 0.932909736, 1.158661932, 1.113810503, 1.072696692]
    z = 0
    for idx, company in enumerate(companies):
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
                        price = product_dim.attributes["list_price"][product]
                        price = round(price * yearly_price_increase, -1) - 1
                        cube[year, month, company, product, "Quantity"] = quantity
                        cube[year, month, company, product, "Sales"] = quantity * price
                        z = z + 2
                yearly_price_increase += (0.01 + random.random() * 0.04)

        if spinner:
            spinner.text = f"Generating data for '{db.name}:{cube.name}' ({z:,} records) -> {company}"
        if callback:
            callback(progress_start + progress_width * idx // len(companies),
                     f"Generating data for cube '{db.name}:{cube.name}' ({z:,} records) -> {company}")


def populate_cube_hr(db: Database, cube: Cube, spinner, callback= None, progress_start=0, progress_width=0):
    """Populate the HR cube"""
    if spinner:
        spinner.text = f"Generating data for '{db.name}:{cube.name}: "

    years = db.get_dimension("years").get_leaves()  # Jan... Dec
    hr_dim = db.get_dimension("employees")
    employees = hr_dim.get_leaves()  # all non aggregated P&L positions
    root_salary = 100000.0
    z = 0
    for idx, employee in enumerate(employees):
        yearly_salary_increase = 1.0
        salary = max(30000.0, round(root_salary * random.gauss(1.0, 0.2), -4))
        for year in years:
            salary = round(salary * yearly_salary_increase, -4)
            cube[year, employee, "Base Salary"] = salary
            cube[year, employee, "Bonus"] = round(random.uniform(0.0, 50000.0), -4)
            claim = 30.0 if random.random() < 0.8 else 25.0
            cube[year, employee, "Holiday claim"] = 30 if random.random() < 0.8 else 25
            cube[year, employee, "Holidays taken"] = claim - float(random.randrange(0, 5, 1))
            z = z + 2
        if spinner:
            spinner.text = f"Generating data for '{db.name}:{cube.name}' ({z:,} records) -> {employee}"
        if callback:
            callback(progress_start + progress_width * idx // len(employees),
                     f"Generating data for cube '{db.name}:{cube.name}' ({z:,} records) -> {employee}")

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
    dim.add_many("Year", ("Q1", "Q2", "Q3", "Q4"))
    dim.add_many(["Q1", "Q2", "Q3", "Q4"],
                 [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                    ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
    dim.add_many(["HY1", "HY2"], [("Jan", "Feb", "Mar", "Apr", "Mai", "Jun"),
                                  ("Jul", "Aug", "Sep", "Oct", "Nov", "Dec")])
    dim.commit()

    # Attributes
    dim.attributes.add("longname", str)
    # first copy the member name as the default long name.
    for member in dim.get_members():
        dim.attributes["longname"][member] = member
    # set proper long names for months
    for member, value in (("Jan", "January"), ("Feb", "February"), ("Mar", "March"),
                 ("Apr", "April"), ("Mai", "Mai"), ("Jun", "June"),
                 ("Jul", "July"), ("Aug", "August"), ("Sep", "September"),
                 ("Oct", "October"), ("Nov", "November"), ("Dec", "December")):
        dim.attributes["longname"][member] = value

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
        d.add_many(str(y))
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
    d.add_many(["Actual", "Plan", "Forecast",
                  "ACTvsPL", "ACTvsPL%",
                  "ACTvsFC", "ACTvsFC%",
                  "ACTvsACTpy", "ACTvsACTpy%",
                  "FCvsPL", "FCvsPL%",
                  "FCvsACTpy", "FCvsACTpy%"])

    d.add_many("ACTvsPL",["Actual", "Plan"], [1.0, -1.0])
    d.add_many("ACTvsFC",["Actual", "Forecast"], [1.0, -1.0])
    d.add_many("FCvsPL",["Forecast", "Plan"], [1.0, -1.0])

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
    dim.add_many(["Gross Sales",
                    "Sales Returns",
                    "Discounts and Allowances"])
    dim.add_many("Net Sales", ["Gross Sales", "Sales returns", "Discounts and Allowances"], [1.0, -1.0, -1.0])
    # Cost of Goods Sold
    dim.add_many(["Raw Materials",
                    "Direct Labor",
                    "Overheads"])
    dim.add_many("Cost of Goods Sold", ["Raw Materials", "Direct Labor", "Overheads"])
    # Gross Profit
    dim.add_many("Gross Profit", ["Net Sales", "Cost of Goods Sold"], [1.0, -1.0])
    # Operating Expenses
    dim.add_many("Operating Expenses",
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

    dim.add_many("Operating Profit", ["Gross Profit", "Operating Expenses"], [1.0, -1.0])
    dim.add_many("Profit Before Taxes", ["Operating Profit", "Interest Income", "Other Income"], [1.0, -1.0, 1.0])
    dim.add_many("Net Profit", ["Profit Before Taxes", "Tax Expense"], [1.0, -1.0])
    dim.commit()

    # Attributes
    # we add an attribute that contains somehow realistic sample values
    # for our P&L figures. These will be used later to generate randomized data.
    dim.attributes.add("sample", float)
    for pair in (("Gross Sales", 78000.0),
                 ("Sales Returns", 3200.0),
                 ("Discounts and Allowances", 1000.0),
                 ("Raw Materials", 8100.0),
                 ("Direct Labor", 10000.0),
                 ("Overheads", 2100.0),
                 ("Advertising", 600.0),
                 ("Delivery/Freight", 1500.0),
                 ("Depriciation", 8000.0),
                 ("Insurance", 550.0),
                 ("Office Supplies", 1300.0),
                 ("Rent/Lease", 5800.0),
                 ("Maintenance and Repairs", 200.0),
                 ("Travel", 200.0),
                 ("Wages", 10000.0),
                 ("Utilities", 800.0),
                 ("Other Expenses", 230.0),
                 ("Interest Income", 1700.0),
                 ("Other Income", 1250.0),
                 ("Tax Expense", 10000.0)):
        dim.attributes.set("sample", pair[0], pair[1])

    # Subsets
    dim.subsets.add("Expenses",
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

    dim.subsets.add("Overview",
                   ["Gross Sales",
                    "Net Sales",
                    "Gross Profit",
                    "Operating Expenses",
                    "Operating Profit",
                    "Profit Before Taxes",
                    "Net Profit"])

    return dim

def add_dimension_countries(db: Database, name:str ="countries", countries_count: int = 10):
    """
    Creates a country dimension.
    """
    dim = db.add_dimension(name).edit()
    # 4 levels e.g. ["World", "EMEA", "Africa", "Egypt", "EGP"]
    index = sorted(random.sample(range(len(entities.countries)), min(countries_count, len(entities.countries))))
    selected_countries = [entities.countries[i] for i in index]
    for country in selected_countries:
        # country = list(reversed(country))
        for i in range(3):
            dim.add_many(country[i], country[i + 1])
    dim.commit()

    # Attributes
    dim.attributes.add("curcode", str)
    for country in selected_countries:
        dim.attributes["curcode"][country[3]] = country[4]

    return dim


def add_dimension_curcodes(db: Database, name: str = "curcodes") -> Dimension:
    """
    Creates a currency code dimension.
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    currencies = entities.currencies

    # create company dimension
    dim = db.add_dimension(name).edit()
    for currency in currencies:
        curcode = currency[0]
        dim.add(curcode)
    dim.commit()

    # Attributes
    dim.attributes.add("code", str)
    dim.attributes.add("numcode", str)
    dim.attributes.add("name", str)
    for currency in currencies:
        curcode = currency[0]
        dim.attributes["code"][curcode] = currency[0]
        dim.attributes["numcode"][curcode] = currency[1]
        dim.attributes["name"][curcode] = currency[2]

    return dim


def add_dimension_currency(db: Database, name: str = "currency") -> Dimension:
    """
    Creates a currency dimension.
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    dim = db.add_dimension(name).edit()
    dim.add("GC")
    dim.add("LC")
    dim.commit()
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

    dim_countries = db.dimensions["countries"]
    countries = dim_countries.leaf_members

    # create company dimension
    dim = db.add_dimension(name).edit()
    if not international:
        dim.add_many(group_name, [fake.company() for i in range(companies_count)])
    else:
        # dim.add_many(group_name, ["EMEA", "NA", "LATAM", "APAC"])
        # select some countries
        max_country = min(int(companies_count // 4), len(countries))
        companies_per_country = companies_count // max_country
        index = list(sorted(random.sample(range(len(countries)), max_country)))
        for i in index:
            member = countries[i]
            hierarchy = list(reversed(member.parent_hierarchy))
            for p in range(1, len(hierarchy)):
                if p == 1:
                    dim.add_many(group_name, hierarchy[p].name)
                else:
                    dim.add_many(hierarchy[p - 1].name, hierarchy[p].name)
            dim.add_many(hierarchy[-1], [fake.company() for i in range(companies_per_country)])
    dim.commit()

    # Attributes
    dim.attributes.add("manager", str)
    for member in dim.get_members():
        dim.attributes["manager"][member] = fake.name()

    dim.attributes.add("curcode", str)
    for member in dim.leaf_members:
        country = dim_countries[member.first_parent.name]
        curcode = country.attribute("curcode", "EUR")
        dim.attributes["curcode"][member] = curcode

    return dim

def add_dimension_company_old(db: Database, name: str = "companies", group_name: str = "Tiny Corp.",
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
        dim.add_many(group_name, [fake.company() for i in range(companies_count)])
    else:
        dim.add_many(group_name, ["EMEA", "NA", "LATAM", "APAC"])
        companies_per_region = int(companies_count / 4)
        for region in ["EMEA", "NA", "LATAM", "APAC"]:
            dim.add_many(region, [fake.company() for i in range(companies_per_region)])
    dim.commit()

    # Attributes
    dim.attributes.add("manager", str)
    for member in dim.get_members():
        dim.attributes["manager"][member] = fake.name()

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

        dim.add_many("All Products", family)
        dim.add_many(family, line)

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
                dim.add_many(line, product)
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
    dim.attributes.add("color", str)
    dim.attributes.add("id", str)
    dim.attributes.add("list_price", float)
    for member in products:
        dim.attributes.set("color", member, fake.color())
        dim.attributes.set("id", member, fake.unique.bothify(text='Product Number: ????-########'))
        dim.attributes.set("list_price", member, float(50 + int(random.random() * 20.0) * 50 - 1))

    return dim


def add_dimension_sales_figures(db: Database, name: str = "salesfig") -> Dimension:
    """
    Dimension defining sales figures
    :param db: The target database.
    :param name: Name of the dimension
    :return: The new dimension.
    """
    d = db.add_dimension(name).edit()
    d.add_many(["Sales", "Quantity", "Price"])
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
            dim.add_many(hierarchy[i], [hierarchy[i - 1]])
        # now add employees
        dim.add_many(company, [fake.name() for i in range(employees_per_company)])
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
    d.add_many(["Base Salary", "Bonus", "Holiday claim", "Holidays taken"])
    d.commit()
    for member in ["Holiday claim", "Holidays taken"]:
        d.member_set_format(member, "{:,.0f}")
    for member in ["Base Salary", "Bonus",]:
        d.member_set_format(member, "{:,.0f}")
    return d
# endregion


# region Rules for Sales
@rule(trigger=["Price"])
def rule_sales_price(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    quantity = c["salesfig:Quantity"]
    if quantity:
        return c["salesfig:Sales"] / quantity
    return None
# endregion

@rule(cube=["pnl","pnl_lcgc"], trigger=["ACTvsPL%"])
def rule_datatype_actvspl_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Plan in %."""
    plan = c["datatype:Plan"]
    if plan:
        return (c["datatype:Actual"] - plan) / plan
    return None

@rule(("pnl","pnl_lcgc"), ["ACTvsFC%"])
def rule_datatype_actvsfc_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Forecast in %."""
    fc = c["datatype:Forecast"]
    if fc:
        return (c["datatype:Actual"] - fc) / fc
    return None

@rule(None, ["FCvsPL%"])
def rule_datatype_fcvspl_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Plan in %."""
    plan = c["datatype:Plan"]
    if plan:
        return (c["datatype:Forecast"] - plan) / plan
    return None


@rule(None, ["FCvsACTpy"])
def rule_datatype_fcvsactpy(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Actual Previous Year."""
    prev_year = c.member("years").previous
    if prev_year:
        return c["datatype:Forecast"] - c["years:" + str(prev_year), "datatype:Actual"]
    return None


@rule(None, ["FCvsACTpy%"])
def rule_datatype_fcvsactpy_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Forecast vs Actual Previous Year in %."""
    prev_year = c.member("years").previous
    if prev_year:
        actual = c["years:" + str(prev_year), "datatype:Actual"]
        if actual:
            return (c["datatype:Forecast"] - actual) / actual
        return None
    return None


@rule(None, ["ACTvsACTpy"])
def rule_datatype_actvactpy(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Actual Previous Year."""
    prev_year = c.member("years").previous
    if prev_year:
        return c["datatype:Actual"] - c["years:" + str(prev_year), "datatype:Actual"]
    return None


@rule(None, ["ACTvsACTpy%"])
def rule_datatype_actvactpy_percent(c: Cell, scope=RuleScope.ALL_LEVELS, volatile=False):
    """Rule to calculate Actual vs Actual Previous Year in %."""
    prev_year = c.member("years").previous
    if prev_year:
        actual = c["years:" + str(prev_year), "datatype:Actual"]
        if actual:
            return (c["datatype:Actual"] - actual) / actual
        return None
    return None


@rule("pnl_lcgc", trigger=["currency:GC"], feeder=["currency:LC"], scope=RuleScope.BASE_LEVEL)
def rule_lc_to_gc(c):
    """
    Base level rule to calculate a value in global currency ('GC') from local currency ('LC').
    This requires to first read the value in local currency, then read the currency code for the
    current region from and attribute, then look up the exchange rate from the exchange rate cube
    named ('exrates') and finally multiply the value with the exchange rate to get the requested
    value in GC.
    """
    # [currency, datatype, years, periods, company, pnl])
    # [datatype, years, periods, curcodes]
    value = c["currency:LC"]  # read the value in local currency
    if value:
        currcode = c.member("companies").attribute("curcode", "EUR")  # read the currency code for the current region
        exrate = c.db["exrates", c.member("datatype"), c.member("years"), c.member("periods"), currcode]  # look up exchange rate
        return value * exrate  # evaluate and return GC value
    return value

# endregion


if __name__ == "__main__":
    # Playtime!!! ʕ•́ᴥ•̀ʔっ
    db = create_database()
    cube = db.cubes["pnl_lcgc"]
    company = db.dimensions['companies'].root_members[0]

    cube.reset_counters()
    start = time.time()
    value = cube[ "GC", "Actual", "2022", "Year", company, "Net Profit"]
    duration = time.time() - start
    print(f"value := {value}")
    print(f"Top most n-rule cell with 1 cells executed in {duration:.3} sec. "
        f"\n\t{cube.counter_cell_requests:,} individual cell requests, "
        f"\n\t{cube.counter_rule_requests:,} rules executed"
        f"\n\t{cube.counter_aggregations:,} cell aggregations "
        f"(thereof {cube.counter_weighted_aggregations:,} weighted)\n")

    cube.reset_counters()
    start = time.time()
    value = cube["LC", "Actual", "2022", "Year", company, "Net Profit"]
    duration = time.time() - start
    print(f"value := {value}")
    print(f"Top most no rule cell with 1 cells executed in {duration:.3} sec. "
        f"\n\t{cube.counter_cell_requests:,} individual cell requests, "
        f"\n\t{cube.counter_rule_requests:,} rules executed"
        f"\n\t{cube.counter_aggregations:,} cell aggregations "
        f"(thereof {cube.counter_weighted_aggregations:,} weighted)")
