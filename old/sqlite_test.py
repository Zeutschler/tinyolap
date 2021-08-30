#!/usr/bin/env python
"""Attempt to see whether :memory: offers significant performance benefits."""
import itertools
import os
import sys
import time
import sqlite3
import numpy as np

max_member_count = 20
dims = [5, 3, 10, max_member_count, 6, 5]  # cube dim sizes
addresses = []


def create_db(conn):
    c = conn.cursor()
    # https://phiresky.github.io/blog/2020/sqlite-performance-tuning/
    c.execute('PRAGMA temp_store=MEMORY;')
    c.execute('PRAGMA journal_mode=MEMORY;')
    #c.execute('PRAGMA synchronous = normal;')
    #c.execute('PRAGMA mmap_size = 30000000000;')
    # c.execute('PRAGMA journal_mode=WAL;')

    # Make a demo table, also multiple vales would be possible
    sql_create_table = f"create table if not exists demo (" \
                       f"{','.join([' id' + str(d+1) + ' int' for d in range(len(dims))]) }" \
                       f", value real " \
                       f", PRIMARY KEY ({','.join([' id' + str(d+1) for d in range(len(dims))]) }) ) WITHOUT ROWID;"
    c.execute(sql_create_table)
    for d in range(len(dims)):
        sql = f"create index id{d+1}_index on demo (id{d+1});"
        c.execute(sql)

    members = [ list(range(1, d+1)) for d in dims]
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

    # 2) Load it into both dbs & build indices
    try:
        os.unlink('foo.sqlite')
    except OSError:
        pass

    conn_mem = sqlite3.connect(":memory:")
    conn_disk = sqlite3.connect('foo.sqlite')
    create_db(conn_mem)
    create_db(conn_disk)

    for con in [conn_disk, conn_mem]:
        z, duration = exec_cell_query(conn_mem)
        print(f"{z:,}x cell queries in {duration:.6f}, {z/duration:,.0f} ops/sec")
        global dims, max_member_count
        for member_count in range(2, max_member_count + 1, 2):
            member_lists = [list(range(1, min((max_member_count, member_count, d)) + 1)) for d in dims]
            z, duration = excec_range_query(conn_mem, member_lists)
            print(f"1x range query in {duration:.6f}, {z:,}x cells returned, "
                  f"{1/duration:,.0f} queries/sec, {z/duration:,.0f} agg/sec")
        print()

if __name__ =="__main__":
    main()