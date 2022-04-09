# TinyOlap 

TinyOlap is a light-weight, client-side, model-driven, cell-oriented, multi-dimensional OLAP 
database for **planning, budgeting, reporting, analysis and many other purposes**. 
Although this sounds very complicated, TinyOlap is actually very easy to use and should 
be also suitable for all Python and database skills levels.

To get started, please visit our documentation: [https://tinyolap.com](https://tinyolap.com)

If you're curious, just clone the repo and check out and run /samples/tiny.py [tiny.py](https://github.com/Zeutschler/tinyolap/blob/main/samples/tiny.py).

TinyOlap is written in plain Python. Not a clever idea for a database, you might think. 
And you're right, TinyOlap is not as fast as comparable commercial products like 
IBM's TM/1, Jedox's Palo, Infor's BI OLAP or SAP HANA or intended to replace such solution. 

But TinyOlap is fast enough for most use cases (especially when we talk about planning). For being made of 
simple Python arrays, dicts and sets only TinyOlap is even **impressively fast**. That said, TinyOlap is not 
intended to be used for any kind of mass data processing, also because it's not very memory effective.  

But TinyOlap has another huge advantage over the mentioned commercial products. **You can write your business 
logic in beautiful Python** and enjoy the [pythonic way](https://www.udacity.com/blog/2020/09/what-is-pythonic-style.html). 
of coding.

Please check and play with the provided examples. **Warning**: the *company.py* example has real-world size and 
complexity for the financial planning and reporting of a large international (fantasy) enterprise. 

**Multi-user support?** TinyOlap is not a client-server database, it resides in your current Python process 
and persists to an SQLite database file. But through the included (optional) web-API, using the great
[Fast-API](https://fastapi.tiangolo.com), you can also build applications that can serve some handfull of users.

## How to use TinyOlap
As said, TinyOlap is a '*model-driven OLAP database*'. That implies, that you first need to build a data model 
defining your data space. Then you can import data, write data to individual cells or areas in the database or enter 
data manually through a frontend. TiynOlap does not (yet) provide a frontend, but an Excel add-in and a web frontend 
are on the list.

### Example
Let's say you need to do a business plan for your car company for the next year based on actual data.
1. The first step is to think about the **dimensions** that best describe your business. e.g., you want plan 
   monthly figures for the upcoming year. The best way is to split this up into 2 separate dimensions, one for 
   the **monthes** and one for the **years**. 
   
   Then you have your **products**, and the **countries** you sell 
   them to. Finally, you need to differentiate between actual and plan, and also have some figures like Sales, 
   Cost and Income. All this accumulates in the following **6 dimensions** fully representing your business:
   - **[datatype]** := Actual, Plan, Forecast
   - **[years]** := 2020, 2021, 2022, ...
   - **[months]** := Jan, Feb, ... , Dec, **Q1**, ... **Q4**, **Year**
   - **[products]** := Model 3, Model S, Model X, **Total**
   - **[countries]** := USA, Canada, Mexico, **North America**, ... , **Europe**, **Total**
   - **[measures]** := Quantity, Sales, Cost, **Income**, Tax, **Net Income**

2. The second and already last step is to **build a cube** - a multidimensional space, equivalent to a table in a 
   relational database - to holds your data. Let's call this cube **'Tesla'**
   - **Cube:[tesla]** := [datatype, years, monyths, products, countries, measures]
   

## Why building an in-memory databse in plain Python? 
TinyOlap started as a by-product of a research project - I simply needed a super-light-weight MOLAP database. 
But there was no, so I build one. TinyOlap is very suitable for educational purposes in computer science as well as 
in business studies. I use TinyOlap for my master class students in "Business Analytics" at the HSD University for 
Applied Science in Düsseldorf (Germany). Although Tinyolap is escpecially helpfull for experimental business purposes.

TinyOlap is also a reminiscence and homage to the early days of OLAP databases, where great products like 
Applix TM/1 or MIS Alea enabled business users to build expressive data models with dimension, cubes and complex 
business logic in just a few minutes our hours. Unfortunately, these products have grown up to complex and 
very expensive client-server database technologies, all striving for the ultimate performance on mass data 
processing and high number of concurrent users.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on 
client-side planning, budgeting, calculations and analysis purposes. TinyOlap provides sub-second 
response for most queries (see limitations below) and supports instant 
*dimensional modelling* - e.g., adding new members to dimensions or adding new calculations.

To support at least some kind of **multiuser scenarios**, TinyOlap provides a very simple, file-based 
asynchronous data synchronization between multiple users and instances of a
database. If you have shared drive, it even becomes a no-brainer. In addition, 
a TinyOlap database can also directly act as a web server to serve a small group 
of users for simple use cases (see limitations).

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
