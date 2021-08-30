# TinyOlap 

TinyOlap is for light-weight **planning, budgeting & reporting** purposes. TinyOlap is a tiny multi-dimensional 
OLAP database, written in Python, using SQLite as backend. It's also great for educational purposes
in business studies, computer science and many other areas.   

## What can you do with TinyOlap
TinyOlap is a '*structure-driven OLAP database*'. That implies, that you first build a data model representing
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
TinyOlap is **freaking fun and fast** with data models up to a million records or even more. but it's not
build for any kind of mass data processing or analysis. 


## How can you use TinyOlap
TinyOlap is inspired by the early days of OLAP databases, and products like TM/1, where users where able
to install a 


delivered in former times. People involved in planning
were able to 
- spin up a new database on a single click (it's a file), 
- build a data model, representing their business or use case with dimension, cubes and business logic 
  in a few minutes our hours, 
- were able to import

Unfortunately, these products 
have grown up to complex (IT required) and very expensive database servers, all striving 
for the ultimate performance on mass data processing.

TinyOlap has a different focus. Although it works fine with millions of records

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
