from unittest import TestCase
import time
from tinyolap.query import Query
from samples.tiny import load_tiny, play_tiny


class TestQuery(TestCase):

    def setUp(self):
        # delete database if exists
        self.database = play_tiny(False)

    def test_execute_sql_queries(self, console_output: bool = True, dump_records: bool = True):
        # None of the following statements should through an error.
        queries = [
            {"sql": "SELECT months, products FroM sAles WHERE '2021', months=summer, North, products='*', 'Sales'"},
            {"sql": "select months, value from sales where '2021', 'Jan', 'North', 'motorcycles', 'Sales'"},
            {"sql": "SELECT * FROM sales WHERE '2021', 'Jan', North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT months, value FROM sales WHERE '2021', 'Jan', North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT regions, regions.manager, months, value FROM saLes WHERE '2021', North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT * FroM sAles WHERE '2021', months=('Jan', 'Feb'), North, 'motorcycles', 'Sales'"},
            {"sql": "SELECT months, products FroM sAles WHERE '2021', months=summer, North, products='*', 'Sales'"},
            {"sql": "SELECT months, value, products FROM sAles WHERE '2021', months=summer, North, products='*', 'Sales'"},
        ]

        for index, query in enumerate(queries):
            sql = query["sql"]
            q = Query(self.database, sql, True)

            start = time.time()
            try:
                success = q.execute()
            except:
                self.fail(f"SQL statement failed unexpectedly: {sql}")

            duration = time.time() - start
            if console_output:
                if success:
                    print(f"{index}: {q.sql}")
                    print(f"\t...query {index} returned {len(q.records):,.0f} records "
                          f"in {duration:.3}sec, {len(q.records) / duration:,.0f} records/sec")

                    if dump_records:
                        print("\n".join([str(record) for record in q.records]))
                        print()
                else:
                    print(f"SQL query {index} failed.")

