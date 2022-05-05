.. _formulas:

===============
Rules
===============

A multidimensional database - like TinyOlap - that can aggregate numbers over hierarchies over multiple dimensions
is already a nice thing. But the real fun begins, when you need to add business logic to your database.
In a relational database you can use triggers and write stored procedures, or you would define you business logic
at query time either by using some advanced SQL statements.

In TinyOlap, all business logic despite simple aggregations can be defined through **rules**. Rules can be seen
as combination of a trigger and a stored procedure. The main difference is, that rules can be written in plain Python,
either as a function, a static class method (using the ``@staticmethod`` decorator) or even as a lambda function.
This allows you to write high structured code and can leverage the entire Python universe for you business logic. Cool!

Once you understand the very basic concept of how to write rules in TinyOlap, you will love the concept. The only
challenge to master is the fact that you do calculations in multi-dimensional space, rather then processing
records of a table. Let's get started.

The basic concept of Rules
--------------------------
Lets take a look at an example to calculate the ``delta in %`` between the two members
``actual`` and ``plan``, defined as ``delta in % = (actual - plan) / plan``.
Let's assume these members are already defined in a dimension called ``datatypes`` and used in a 4-dimensional
cube called ``sales``.

The first step of writing proper rules is always to think about, what parts of the business logic can already be solved
outside the rule, through the build-in weighted aggregation of TinyOlap cubes. So instead of doing the full calculation
in the rule, we first introduce a new member ``delta`` that adds up the member ``actual`` with a weight of 1.0 and ``plan``
with a weight of -1.0. Now we can already simplify the business logic to ``delta in % = delta / plan``.
So the dimension then looks something like this:

.. code:: python

    actual
    plan
    delta
        actual +1.0
        plan   -1.0
    delta in %

Now we can write our first rule. The details will be explained later.

.. code:: python
    from tinyOlap.cell import Cell

    @rule(cube="sales", trigger="datatypes:delta in %")
    def rule_sales_delta_in_percent(c: Cell):
        return c["delta"] / c["plan"]


This rule code already represents an 'almost' proper written rule. Although rules can also be written, registered
and used without the ``@rule`` decorator, it should become your best practise to **always** use the ``@rule`` decorator
when writing rules. It simply makes you business logic much more explicit, readable and maintainable.

Rules usually consists of 3 main parts:

- The ``@rule`` decorator, defining the behavior and assignment of a rule. Primarily this is...

  - the TinyOlap *cube* the which the rule should be assigned to. Each individual rule should be assigned to 1 cube only.

  - the *trigger* for the rule. This normally is a cell address pattern that defines a single member or multiple members
    from one or multiple dimension. In the sample above it is just the single ``datatypes:delta in %`` member from the
    ``datatypes`` dimension. Although TinyOlap is able to resolve a trigger without explicitly naming the dimension -
    so ``delta in %`` would also be sufficient - it is best practise to always use the dimension. First because the
    member could be defined in multiple dimensions; >think of a ``Total`` member in a products and in a regions
    dimension, which one should be addressed by a rule? Second, when someone else needs to maintain your business logic
    and has no clue about your data model, who should this person be able to understand the multidimensional context
    of your rule.

  - some settings that define when and how the rule should behave or treated. We'll come back to this later.

- The function signature which needs to look like this ``def any_function_name(c: Cell):``. Some tpyes of rules
  also require more call parameters, we'll get this later.
  The name of the function can be anything, but should ideally express for everyone who may ever will see the rule,
  what the rule is actually doing or calculating. A best practice is to start your rule name with the prefix ``rule_``.
  To make it even more explicit you can/should use the following prefix pattern ``rule_[name of cube]_``. This also
  greatly helps to debug your rules.

  The call signature of the function must contain at least one single parameter ``c`` which represents the cell context
  (the address in the cube) as requested from the user. It is highly beneficial to use the ``Cell`` type hint at
  all time, especially to benefit from code assistance in your IDE of choice. If you want to call the rule function
  on your own and you require additional parameters, then these need to be optional as the TinyOlap engine will call
  the function with only one parameter, the current cell context ``c``.

  The ``Cell`` type hint allows you to navigate through and access the data space, starting from the requested cell
  address. Actually it's a cursor. As shown in the example below, you can easily "walk" through the data space by
  repositioning or shifting or investigating the data space. ``c["delta"]`` as an example, temporarily shifts the
  cursor from member ``c["delta in %"]`` to member ``c["delta"]``. As ``Cell`` objects behave like ``float`` values,
  you can directly use them in mathematical calculations. In the background TinyOlap always goes down to the cube
  and (tries to) returns its current value.

- The value to returned. Most rules calculate something and return a value. This can be any datatype, also text,
  datetime or even mre complex objects, but most often it either will be a ``float`` value, the result of your
  calculation, or ``None``, if your rule calculation does not provide a meaningful result.


If your rule create an error, it will automatically be caught by the TinyOlap engine to not crash the entire system.
Users will then see an error message instead of a cell-value in the cell that cause the error. But your ambition
should be to not raise any error and provide a robust business logic. The most common error with rules are 1. division
by zero error and 2. typos in member names and 3. changes to dimensions not reflected in the rules.

No let us optimise the rule so that it ideally did not raise any error. As ``None`` is the default result for any
function in Python, you do not explicitly return ``None``. Please also note that ``plan = c["plan"]`` helps to
reference the ``plan`` cell just once.

.. code:: python

    @rule(cube="sales", trigger="datatypes:delta in %")
    def rule_profit(c: Cell):
        plan = c["plan"]
        if plan:
            return c["delta"] / plan

If your members names do not contain special characters and comply with the standard Python naming conventions, it also
possible to write rules a bit more *pythonic*, through direct attribute access. But this has quite some limitations
(already ``delta in %`` would not translatable into a proper attribute name). Whitespaces `` `` will be translated
to underscores ``_``, so ``fun stuff`` would become ``fun_stuff``. In addition, as everywhere in TinyOlap, naming
is case insensitive. A valid example:

.. code:: python

    @rule(cube="sales", trigger="datatypes:delta in %")
    def rule_profit(c: Cell):
        plan = c.plan  # ...very pythonic
        if plan:
            return c.delTA / plan  # 'delTA' is not a problem


The Scope of Rules
------------------
There are various situations how and when a rule is called

-   **ALL_LEVELS** - (default) Indicates that the rule should be executed for base level
    and aggregated level cells.

-   **AGGREGATION_LEVEL** - Indicates that the rule should be executed for aggregated level cells only.

-   **BASE_LEVEL**  - Indicates that the rule should be executed for base level cells only.
    For aggregated values, all of base level cells that make up the aggregation, will be calculated through the rule and only then get aggregated.

-   **ON_ENTRY** - Indicates that these rules should be executed when cell values are set or changed.
    You then can handle the user input somehow.
    This is for instance very useful when real time calculations would become *too expensive* to run and if you have really
    complex business logic to calculate. Two classic examples: 1. the 'depreciation of an asset' over time, many values need to
    be calculated and written to the database, or 2. on automated forecast of a time series in your cube, quite complex calculations needed.

-   **COMMAND**- Very close to **ON_ENTRY**, but reacts more on specific keywords or values. It indicates that such
    rules need to be invoked by a command. This requires the decorator parameter ``command`` to specify one or more
    keywords that should trigger the command, e.g. ``command=["forecast", "predict"]`` to react when the user types
    forecast or predict. Also wildcards are supported, ``command=["f*"]`` would enable your rule to react upon really
    all ``f*`` words, e.g. ``forecast``.
    So to write a rule that does an automated forecast when a user types in the word "forecast" would look like this:

    .. code:: python

        @rule(cube="sales", trigger="datatypes:forecast", scope=RuleScope.COMMAND, command=["forecast", "predict"])
        def rule_profit(c: Cell):
            # the rule will only called when users enter either "forecast", "predict" or "*" on a cell that
            # refers to the member "forecast" in dimension datatypes.

            # do some magic forecasting stuff here...
            # or do whatever you would like to do, e.g. open up the browser and show a nice cat video ;-).
            pass

    Tip: You should not forget to explain and demonstrate to your users, what command capability actually exists.


Registering rules
-----------------


Simple Rules
------------

Sample of a proper rule:

.. code:: python

    @rule("sales", ["avg. price"], scope=RuleScope.ALL_LEVELS, volatile=False)
    def rule_average_price(c : tinyolap.context):
        quantity = c["quantity"]
        sales = c["sales"]
        # ensure both values exist or are of the expected type (cell values can be anything)
        if quantity is float and sales is float:
            if quantity != 0.0:
                return sales / quantity
            return "n.a."  # the rule developer decided to return some text. That is totally fine.
        return c.CONTINUE


Now, every time a cell is requested that contains the member ``delta in %``, this rule will be called
and the value returned from the rule will be shown to the user (as it would be returned from the cube).





.. autoenum:: tinyolap.rules.RuleScope
    :members:
    :noindex:

.. autoenum:: tinyolap.rules.RuleInjectionStrategy
    :members:
    :noindex:

.. autoclass:: tinyolap.rules.Rules
    :members:
    :noindex: