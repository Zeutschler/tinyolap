#!/usr/bin/env python
"""Attempt to see whether :memory: offers significant performance benefits."""
import itertools
import os
import sys
import time
import sqlite3

max_member_count = 20
dims = [5, 3, 10, max_member_count, 10, 6]  # cube dim sizes
addresses = []


def create_db(conn):

    start = time.time()
    c = conn.cursor()
    # https://phiresky.github.io/blog/2020/sqlite-performance-tuning/
    c.execute('PRAGMA temp_store=MEMORY;')
    c.execute('PRAGMA journal_mode=MEMORY;')
    #c.execute('PRAGMA synchronous = normal;')
    #c.execute('PRAGMA mmap_size = 30000000000;')
    # c.execute('PRAGMA journal_mode=WAL;')

    # Make a demo table, also multiple vales would be possible
    sql_create_table = f"create table if not exists demo (" \
                       f"{','.join([' id' + str(d+1) + ' int' for d in range(len(dims))]) }, " \
                       f"value real, " \
                       f"PRIMARY KEY ({','.join([' id' + str(d+1) for d in range(len(dims))]) }) ) " \
                       f"WITHOUT ROWID;"
    c.execute(sql_create_table)
    # for d in range(len(dims)):
    #    sql = f"create index id{d+1}_index on demo (id{d+1});"
    #    c.execute(sql)

    members = [list(range(1, d+1)) for d in dims]
    global addresses
    addresses = list(itertools.product(*members))
    z = 0
    for id in addresses:
        sql = f"insert into demo values({', '.join([str(d) for d in id])}, 1.0);"
        result= c.execute(sql)
        z = z + 1
        if z % 1000 == 0:
            sys.stdout.write(f"\r Inserting records {z/len(addresses):.2%}")
            sys.stdout.flush()
    sys.stdout.write(f"\r")
    sys.stdout.flush()

    c.execute('PRAGMA vacuum;')
    c.execute('PRAGMA optimize;')
    conn.commit()
    duration = time.time() - start
    print(f"Created and fill database with {z:,}x cells in {duration:.6f} sec, {z / duration:,.0f} ops/sec")


def exec_query(cursor, query):
    start = time.time()
    foo = cursor.execute(query).fetchall()
    diff = time.time() - start
    return diff


def exec_cell_query(cursor):
    z = 0
    global addresses
    start = time.time()
    for id in addresses:
        sql = f"SELECT value FROM demo WHERE {' AND '.join([' id' + str(i+1) + ' = ' + str(d) for i, d in enumerate(id)])};"
        records = cursor.execute(sql).fetchall()
        if records:
            value = records[0][0]
        else:
            value = 0.0
        z = z + 1
        if z % 1000 == 0:
            sys.stdout.write(f"\r Executing queries {z / len(addresses):.2%}")
            sys.stdout.flush()
    sys.stdout.write(f"\r")
    sys.stdout.flush()
    duration = time.time() - start
    return z, duration

def exec_upsert(conn):
    """CREATE TABLE phonebook2(
          name TEXT PRIMARY KEY,
          phonenumber TEXT,
          validDate DATE
        );
        INSERT INTO phonebook2(name,phonenumber,validDate)
          VALUES('Alice','704-555-1212','2018-05-08')
          ON CONFLICT(name) DO UPDATE SET
            phonenumber=excluded.phonenumber,
            validDate=excluded.validDate
          WHERE excluded.validDate>phonebook2.validDate;"""
    z = 0
    global addresses
    start = time.time()
    cursor = conn.cursor()
    for z in range(len(addresses)):
        id = addresses[z]

        if False:
            sql = f"SELECT value FROM demo WHERE {' AND '.join([' id' + str(i+1) + ' = ' + str(d) for i, d in enumerate(id)])};"
            records = cursor.execute(sql).fetchall()
            if records:
                value = records[0][0]
            else:
                value = 0.0

        value = 2.0
        sql = f"INSERT INTO demo VALUES({', '.join([str(d) for d in id])}, {value}) " \
              f"ON CONFLICT({', '.join(['id' + str(i+1) for i, d in enumerate(id)])}) " \
              f"DO UPDATE SET value=excluded.value;"
        cursor.execute(sql)
        z = z + 1
        if z % 1000 == 0:
            sys.stdout.write(f"\r Executing queries {z / len(addresses):.2%}")
            sys.stdout.flush()
    conn.commit()
    sys.stdout.write(f"\r")
    sys.stdout.flush()
    duration = time.time() - start
    return z, duration




def excec_range_query(cursor, member_lists):
    # generate sql statement for range query
    member_list_text = []
    for i, ml in enumerate(member_lists):
        member_list_text.append(f" id{i+1} in ({','.join([str(m) for m in ml])})")
    where_clause = ' AND '.join([m for m in member_list_text])
    sql = f"select value from demo where {where_clause};"

    # execute range query
    total = 0.0
    start = time.time()
    records = cursor.execute(sql).fetchall()
    if records:
        # aggregate all records
        total = sum([v[0] for v in records])
    duration = time.time() - start
    return int(total), duration


def main():

    print(f"SQLite version {sqlite3.sqlite_version}")

    try:
        os.unlink('db/test.db')
    except OSError:
        pass

    conn_mem = sqlite3.connect(":memory:")
    conn_disk = sqlite3.connect('db/test.db')
    create_db(conn_mem)
    create_db(conn_disk)

    for con in [conn_disk, conn_mem]:
        z, duration = exec_cell_query(con)
        print(f"{z:,}x cell queries in {duration:.6f} sec, {z/duration:,.0f} ops/sec")

        global dims, max_member_count
        for member_count in range(2, max_member_count + 1, 2):
            member_lists = [list(range(1, min((max_member_count, member_count, d)) + 1)) for d in dims]
            z, duration = excec_range_query(con, member_lists)
            print(f"1x range query in {duration:.6f} sec, {z:,}x cells returned, "
                  f"{1/duration:,.0f} queries/sec, {z/duration:,.0f} agg/sec")

        z, duration = exec_upsert(con)
        print(f"{z:,}x upserts in {duration:.6f} sec, {z / duration:,.0f} ops/sec")

        print()

def main_backend():
    from tinyolap.old.backend import Backend

    max_member_count = 20
    dims = [5, 3, 10, max_member_count, 10, 6]  # cube dim sizes
    dim_ids = [1, 2, 3, 4, 5, 6]
    measure_ids = [1, 2, 3, 4, 5, 6]
    measure_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    members = [list(range(1, d+1)) for d in dims]
    addresses = list(itertools.product(*members))

    b = Backend()
    b.delete("db/tiny.db")
    b.open("db/tiny.db")
    b.cube_add("demo", dims, measure_ids)

    start = time.time()
    z = 0
    for address in addresses:
        # b.cube_set("demo", address, 1, 1.0)
        b.cube_set_many("demo", address, measure_ids, measure_values)
        z = z + 1
        if z % 1000 == 0:
            sys.stdout.write(f"\r Adding cells {z/len(addresses):.2%}")
            sys.stdout.flush()
    duration = time.time() - start
    sys.stdout.write(f"\r")
    sys.stdout.flush()
    print(f"{z * len(measure_ids):,}x cells added in {duration:.6f} sec, {z* len(measure_ids) / duration:,.0f} ops/sec")

    b.commit(True)

    start = time.time()
    z = 0
    for address in addresses:
        value = b.cube_get("demo", address, 1)
        z = z + 1
        if z % 1000 == 0:
            sys.stdout.write(f"\r Reading cells {z / len(addresses):.2%}")
            sys.stdout.flush()
    duration = time.time() - start
    sys.stdout.write(f"\r")
    sys.stdout.flush()
    print(f"{z:,}x cells read in {duration:.6f} sec, {z / duration:,.0f} ops/sec")

    for member_count in range(2, max_member_count + 1, 2):
        member_lists = [list(range(1, min((max_member_count, member_count, d)) + 1)) for d in dims]
        start = time.time()
        records = b.cube_get_range("demo", member_lists, 1)
        if records:
            # aggregate all records
            z = sum([v[0] for v in records])
        duration = time.time() - start
        print(f"1x range query in {duration:.6f} sec, {z:,}x cells returned, "
              f"{1 / duration:,.0f} queries/sec, {z / duration:,.0f} agg/sec")

    b.close()


if __name__ =="__main__":
    main_backend()
    # main()
