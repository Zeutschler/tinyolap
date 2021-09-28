# TinyOlap 

TinyOlap is a light-weight model-driven multi-dimensional database for **financial planning, budgeting, business calculations and data analysis** written in plain Python. Sounds quite complicated, but TinyOLap is actually very easy to use, see code sample below, and should be suitable even for absolute Python beginners.

All calculations in TinyOlap are executed on-the-fly, any change to a adatbase is instantly refleced - perfect for planning and data entry purposes. In addition TinyOlap provides some (optional) built-in caching capabilities

TinyOlap should be **fun and fast** with data models up to a million records or even slightly more. Thast said, TinyOlap is not intended to be used for any kind of mass data processing or analysis. 

## How to use TinyOlap
TinyOlap is a '*model-driven OLAP database*'. That implies, that you first build a data model representing
your use case. Then you can import data or enter data manually (what is planning and budgeting is all about). 

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
   - **[masures]** := Quantity, Sales, Cost, **Income**, Tax, **Net Income**

2. The second and already last step is to **build a cube** - a multidimensional space - to holds your data. 
   Let's call that space **'Tesla'**
   - **[products]** := Model 3, Model S, Model X, **Total**

not a value-driven OLAP Database. The focus is on multidimensional modelling. 



## Why building an in-memory databse in plain Python? 
TinyOlap started as a by-product of a research project - I needed a super-light-weight MOLAP database. But there was no, so I build one. TinyOlap is very suitable for educational purposes in computer science as well as in business studies. I use TinyOlap for my master class students in "Business Analytics" at the HSD University for applied science in Düsseldorf (Germany). Although Tinyolap might be of help for experimental business purposes, it is neither suitable nor recommend to be used for any kind of production purposes.


TinyOlap is also a reminiscence and homage to the early days of OLAP databases, where great products like Applix TM/1 or MIS Alea enabled business users to 
build expressive data models with dimension, cubes and complex business logic in just a few minutes our hours. Unfortunately, these products 
have grown up to complex and very expensive client-server database technologies, all striving for the ultimate performance on mass data processing and high number of concurrent users.

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
