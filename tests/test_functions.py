from unittest import TestCase

from decorators import rule
from tinyolap.server import Server
from tinyolap.cell import Cell
from tinyolap.slice import Slice
from tinyolap.rules import RuleScope


class TestBaseFunction(TestCase):
    pass

    def setUp(self) -> None:
        # Create a small test database
        self.server = Server()
        self.db = self.server.create_database("test", in_memory=True)
        db = self.db

        dim_datatype = db.add_dimension("datatype")
        dim_datatype.edit()
        dim_datatype.add_member(["actual", "plan", "var", "var%"])
        dim_datatype.commit()

        dim_years = db.add_dimension("years")
        dim_years.edit()
        dim_years.add_member(["2020", "2021", "2022"])
        dim_years.commit()

        dim_months = db.add_dimension("months")
        dim_months.edit()
        dim_months.add_member(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        dim_months.add_member(["Q1", "Q2", "Q3", "Q4"], [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                                                         ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
        dim_months.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
        dim_months.commit()

        dim_products = db.add_dimension("products")
        dim_products.edit()
        dim_products.add_member("Total", ["A", "B", "C"])
        dim_products.commit()

        dim_measures = db.add_dimension("measures")
        dim_measures.edit()
        dim_measures.add_member(["Sales", "Cost", "Profit"])
        dim_measures.commit()

        self.cube = db.add_cube("sales", [dim_datatype, dim_years, dim_months, dim_products, dim_measures])

    def test_formula(self):

        # Order of rules matter
        self.cube.register_rule(lambda x: "hallo B", ["products:B"], RuleScope.ALL_LEVELS)
        self.cube.register_rule(self.calc_var, ["datatype:var"])
        self.cube.register_rule(self.calc_var_percent, ["datatype:var%"])

        # write some values to the cube
        c = self.cube.cell("actual", "2021", "Jan", "A", "Sales")
        c["actual"] = 250.0
        c["plan"] = 200.0
        c["actual", "2022"] = 300.0
        c["plan", "2022"] = 280.0

        var = c["var"]
        var_perc = c["var%"]
        self.assertEqual(50.0, var)
        self.assertEqual(0.25, var_perc)

        s = {"columns": [{"dimension": "datatype"}, {"dimension": "years"}],
             "rows": [{"dimension": "months"}, {"dimension": "products"}]}
        s = {"columns": [{"dimension": "datatype"}],
             "rows": [{"dimension": "years"}, {"dimension": "products"}]}
        report = Slice(self.cube, s)
        # print(report)

    @rule("sales", ["var"], RuleScope.ALL_LEVELS)
    def calc_var(self, c: Cell):
        return c["actual"] - c["plan"]

    @rule("sales", ["var%"], RuleScope.ALL_LEVELS)
    def calc_var_percent(self, c):
        plan = c["plan"]
        if plan != 0:
            return round((c["actual"] - plan)/plan, 2)
        else:
            return None
