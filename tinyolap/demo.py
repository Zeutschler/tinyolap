import time
from tinyolap.old.cube import Cube
from tinyolap.old.dimension import Dimension
from slice import Slice


def tiny_olap_demonstration():
    # TinyOlap is a simple multidimensional in-memory OLAP database written in plain Python.
    # It's build and intended to be used for demonstration, research or educational purposes.
    # TinyOlap is not memory efficient or fast on larger datasets.

    # HERE'S HOW YOU CAN BUILD, FILL AND ANALYSE A CUBE

    # 1. Create some dimensions and members
    dim_years = Dimension("Years")
    # This is a flat dimension, members have no parents and therefore no aggregation hierarchy.
    dim_years.member_add("2020")
    dim_years.member_add("2021")
    dim_years.member_add("2022")

    dim_periods = Dimension("Periods")
    # This is a hierarchical dimension, all quarters add up to 'Year'.
    dim_periods.member_add("Q1", "Year")
    dim_periods.member_add("Q2", "Year")
    dim_periods.member_add("Q3", "Year")
    dim_periods.member_add("Q4", "Year")

    dim_regions = Dimension("Regions")
    # This dimension defines multiple hierarchy levels.
    dim_regions.member_add("North", "NW")
    dim_regions.member_add("South", "SE")
    dim_regions.member_add("West", "NW")
    dim_regions.member_add("East", "SE")
    dim_regions.member_add("NW", "Total")
    dim_regions.member_add("SE", "Total")

    dim_products = Dimension("Products")
    # This dimension adds single members to multiple parents.
    dim_products.member_add("A", "Total")
    dim_products.member_add("B", "Total")
    dim_products.member_add("C", "Total")
    dim_products.member_add("D", "Total")
    dim_products.member_add("A", "ABC")
    dim_products.member_add("B", "ABC")
    dim_products.member_add("C", "ABC")
    dim_products.member_add("A", "AD")
    dim_products.member_add("D", "AD")

    # 2. define a set of measures. These represent the values stored in a Cube for each cell.
    measures = ["Sales", "Cost", "Profit", "Profit in %"]

    # 3. Create a Cube. Cubes contain at least 2 dimension and 1 measure.
    cube = Cube("Sales", [dim_years, dim_periods, dim_regions, dim_products], measures)

    # 4. You can also add calculation logic to cube measures by defining formulas.
    #    All mathematical operations provided by Python itself and by the Python 'math' module are supported.
    #    All measure references used in your formula must be placed in squared brackets [...].
    #    Otherwise they will not be recognized and compilation will very likely fail. formulas have the gernal form
    #
    #        [Measure] = <some calculation with some other measures>, e.g.: [Profit] = [Sales] - [Cost]
    #
    #    To support real world requirements, 3 types of Formulas are required and needed to be differentiated:
    #    1. Universal formulas (no prefix)- These calculate and return a value for both base-level and aggregated cells.
    #       They do not affect any data in cubes, but are calculated when you request values from a cube.
    #       They are useful for calculations that need return consistent result for both base-level and aggregated
    #       cells, e.g., for a static tax calculation
    #
    #       [Sales incl. Tax] = [Sales] * 1.2
    #
    #    2. Push-down formulas (with prefix 'P:') - These will executed ONLY when a value will be set to the cube and
    #       the measure for write back is contained is one or more formulas. So, the measure is a trigger for the
    #       push down formula to be executed. The result will writen (or 'pushed down') to the targeted measure
    #       in the cube. e.g.:
    #
    #       P:[Revenue] = [Quantity] * [Price]
    #
    #       Whenever [Quantity] or [Price] will be changed, [Revenue] will be recalculated and written to the cube.
    #       If now [Revenue] itself is a trigger to another 'P:' formula, then also these will be executed. This often
    #       can cause quite some calculations and write operations to execute.
    #
    #    3. Aggregation formulas (with prefix 'A:') - These calculate and return a value only for aggregated cells.
    #       They are useful and needed for calculations that should NOT return the same result for base-level and
    #       aggregated cells. e.g. (and to complement the above example):
    #
    #       A:[Price] = [Revenue] / [Quantity]
    #
    #       This corrects the mistaken aggregation of [Price] and return an average Price instead.

    # Lets define a formula.
    cube.add_formula("[Profit] = [Sales] - [Cost]")

    # 4. Write some values to your Cube. Simply by defining your address (as a tuple) and a measure.
    cube.set(("2020", "Q1", "North", "A"), "Sales", 1.0)
    cube.set(("2020", "Q1", "North", "A"), "Cost", 0.8)
    cube.set(("2020", "Q1", "North", "A"), "Profit", 0.2)
    cube.set(("2020", "Q2", "South", "A"), "Sales", 1.0)
    cube.set(("2021", "Q3", "East", "B"), "Cost", 1.0)
    cube.set(("2021", "Q1", "West", "C"), "Cost", 1.0)

    # 4.a You can also write values like this:
    cube.set(("2022", "Q1", "North", "A"), ("Sales", "Cost"), (1.0, 0.7))

    # 4.b ...or even like this. This would write the values to the measures in the order the measures have been defined.
    cube.set(("2022", "Q1", "West", "A"), None, (1.0, 0.7, 0.3))  # Sales=1.0, Cost=0.7, Profit=0.3

    # 5. Reading values from your Cube is also straight forward.
    value = cube.get(("2020", "Q1", "North", "A"), "Sales")
    print(f"{('2020', 'Q1', 'North', 'A')}, 'Sales' := {value}")

    # 5.a You can also get some selected measures at once.
    value = cube.get(("2020", "Q1", "North", "A"), ("Sales", "Cost"))
    print(f"{('2020', 'Q1', 'North', 'A')}, 'Sales and Cost' := {value}")

    # 5.b ...or even all at once. This returns a list of the values for all measures.
    value = cube.get(("2020", "Q1", "North", "A"))
    print(f"{('2020', 'Q1', 'North', 'A')}, 'Sales, Cost, Profit' := {value}")

    # 6. And here's the reasons why you want to use an OLAP database: fast aggregations.
    #    Please note that the following request adds up data for '2020' and measure 'Sales' only := 2.0
    value = cube.get(("2020", "Year", "Total", "Total"), "Sales")
    print(f"{('2020', 'Year', 'Total', 'Total')}, 'Sales' := {value}")

    # 7. It's reporting time! Slicing reports and displaying using a dictionary or plain json.
    #    Definitions for 'rows' and 'columns' are mandatory, 'header' is recommended, the rest is optional.
    #    If no specific members are defined, then all members of the dimension will be shown.
    #    If not all dimensions or no measures defined in the slice, then default values will be assumed
    #    and these will be added to the header. Therefore the following minimal definition is valid:
    definition = {"columns": [{"dimension": "Years"}], "rows": [{"dimension": "Periods"}]}
    print(Slice(cube, definition))

    # 7.a. Normally you would define all dimensions properly and maybe add a title
    #      and use some nice color scheme for your visualization
    start = time.time()
    definition = {
        "title": "TinyOlap Slice",
        "description": "This is a nice slice from a cube. Yummy...",
        "header": [{"dimension": "Years", "member": "2020"},
                   {"dimension": "Regions", "member": "Total"}],
        "columns": [{"dimension": "Periods", "member": "*"},
                    {"measure": ["Sales", "Cost", "Profit"]}],
        "rows": [{"dimension": "Products", "member:": ["Total", "A", "B", "C", "D"]}]
    }
    grid = Slice(cube, definition).as_console_output(color_sheme=Slice.Color_Scheme_Default())
    print(grid)
    print(f"\nThis slice was updated and printed in {time.time()-start: .5f} sec. ")

    # ... more examples to come! They can be found in folder 'examples'.


if __name__ == "__main__":
    tiny_olap_demonstration()
