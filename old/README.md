# TinyOlap
***- under development -***

A lightweight multidimensional database for planning, budgeting and reporting 
purposes, based on SQLite and Python.

## Why you should use TinyOlap
TinyOlap is intended to bring back the easy of use, that client-based OLAP 
databases like TM/1, MIS-Alea or Palo provided in former times. These products 
have been grow up to complex and expensive client-server solutions, definitely 
capable for todays high volume data analysis, but hard to manage for non-IT 
people. 

> If you are a **sales or a finance person** and want to do planning and 
> reporting, or if you are an **IT person** and have to serve such audience 
> then TinyOlap might be for you!

In contrast, TinyOlap is intended to be **cheap (free), simple and focussed** on 
client-side planning, budgeting and reporting. TinyOlap provides sub-second 
response for most queries (see limitations below) and supports instant 
*dimensional modelling* - e.g., adding new members to a dimension.

To support **multiuser scenarios**, TinyOlap provides a very simple, file-based 
asynchronous data synchronization between multiple users and instances of the
database. If you have shared drive, it even becomes a no-brainer. In addition, 
a TinyOlap database can also directly act as a server to serve a smaller team 
of users (see limitations).

## Limitations
As of today, TinyOlap is built upon the relational database SQLite 
(https://www.sqlite.org). This implies that TinyOlap is subject to certain 
limitations, for instance:

- SQLite is not a client-server database, so TinyOlap is not one.
  Saying that, TinyOlap in server-mode should serve a team of up to 10 users 
  just fine.
- TinyOlap is not intended for mass data processing. Although also more than
  1 million records will work fine, it can get a bit too slow for your use. 
  case. That said, 1 million records is already huge amount of data a planning
  & reporting purposes.
- The calculations capabilities of TinyOlap are sufficient for most
  planning uses cases. But still - especially when comapre to products like 
  TM/1 - they maybe not sufficient for advanced use cases. 

## Usage 

Please give it a try
