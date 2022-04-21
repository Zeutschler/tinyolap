.. _members:

=====================
Members & MemberLists
=====================

When you start to implement certain business logic - either in the form of rules, or when you build your
own data processing logic - you will instantly recognize then you have to deal a lot with dimension members
and lists of members. The classes **Member** and **MemberList** provide many convenience features to make
working with members and member lists as easy as possible.

All methods that do not requires arguments have been implemented as properties. This allows easy chaining
of subsequent methods and makes your code (hopefully) a bit more readable. Here"s an example:

.. code:: python

    db = Database("life_is_beautiful")
    ...
    animals = db.dimension["animals"]
    the_first_bear = animals.member.filter("*bear*").first
    sub_species_of_the_first_bear = the_first_bear.leaves

------
Member
------

.. autoclass:: tinyolap.member.Member
    :members:
    :noindex:

----------
MemberList
----------

.. autoclass:: tinyolap.member.MemberList
    :members:
    :noindex:
