from unittest import TestCase
import time
from tinyolap.query import Query
from samples.tiny import load_tiny, play_tiny


class TestQuery(TestCase):

    def setUp(self):
        # delete database if exists
        self.database = play_tiny(False)

    def test_execute_sql_queries(self, console_output: bool = True, dump_records: bool = False ):
        queries = [
            {"sql": "select '2021', 'Jan', 'North', 'motorcycles', 'Sales' from sales"},
            {"sql": "SELECT * FROM sales WHERE '2021', 'Jan', North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT months, value FROM sales WHERE '2021', 'Jan', North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT months, value FROM saLes WHERE '2021', North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT * FroM sAles WHERE '2021', months=('Jan', 'Feb'), North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT * FroM sAles WHERE '2021', months=summer, North, products='*', 'Sales'"},
        ]

        for index, query in enumerate(queries):
            sql = query["sql"]
            q = Query(self.database, sql)

            start = time.time()
            success = q.execute()
            duration = time.time() - start
            if console_output:
                print(f"SQL query {index} returning {len(q.records):,.0f} records "
                      f"in {duration:.3}sec, {len(q.records)/duration:,.0f} records per second")
                if dump_records:
                    print("\n".join([str(record) for record in q.records]))
