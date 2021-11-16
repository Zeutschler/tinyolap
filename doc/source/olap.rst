

https://clickhouse.com/docs/en/

Sooo Falsch...

**Key Properties of OLAP Scenario**

The vast majority of requests are for read access.
Data is updated in fairly large batches (> 1000 rows), not by single rows; or it is not updated at all.
Data is added to the DB but is not modified.
For reads, quite a large number of rows are extracted from the DB, but only a small subset of columns.
Tables are “wide,” meaning they contain a large number of columns.
Queries are relatively rare (usually hundreds of queries per server or less per second).
For simple queries, latencies around 50 ms are allowed.
Column values are fairly small: numbers and short strings (for example, 60 bytes per URL).
Requires high throughput when processing a single query (up to billions of rows per second per server).
Transactions are not necessary.
Low requirements for data consistency.
There is one large table per query. All tables are small, except for one.
A query result is significantly smaller than the source data. In other words, data is filtered or aggregated, so the result fits in a single server’s RAM.