.. _formulas:

===============
Rules
===============
A multidimensional database - like TinyOlap - that can aggregate numbers over hierarchies is already a nice thing.
But the real fun begins, when you want to add business logic to your database. In a relational database you can use
triggers and write ystore procedures, or define you business logic at query time either by individual SQL statements
or by views.

In TinyOlap, all business logic despite simple aggregations can be defined through **rules**. Rules can be seen
as combination of a trigger and a stored procedure. The main difference is, that rules can be written in plain Python,
either as a function, a static class method (using the ``@staticmethod`` decorator) or even as a lambda function.
This allows you to write high structured code and leverage the entire Python universe for you business logic. Cool!

Once you understand the basic concept of how to write rules, you will that it is very simple and straight forward
to define your custom business logic.

The basic concept of Rules
--------------------------
Lets take a look at an example to calculate the *delta* between *actual* and *plan* values in a cube called *sales*.
Let's assume all of these 3 members are defined in the same dimension *datatype*.

The following rule code fragment represents a proper written rule. Although rules can also be written and registered
without the ``@rule`` decorator, it should become your best practise to **always** use the ``@rule`` decorator
when writing rules. It simply makes you business logic much more readable and maintainable.

Rules usually consists of 3 main parts:

- The ``@rule`` decorator, defining the behavior and assignment of a rule. Primarily this is...

  - the TinyOlap cube the which the rule should be assigned to. Ech individual rule should be assigned to 1 cube only.

  - the trigger for the rule. This normally is a cell address pattern that defines a single member or multiple members
    from one or multiple dimension. In the sample below it is just 1 member from one dimension called *delta*.
    Every time a cell or report is requested that contains (addresses) the member *delta*, then this rule will be
    executed and the value returned from the rule will be shown to the user (returned from the cube).

  - some settings that define when and how the rule should behave or treated. We'll come back to this later.

- The function signature which is always should look like this ``def any_function_name(c: CellContext):``.
  The name of the function can be anything, but should ideallyc express what the rule is doing.
  The call signature must contain at least one single parameter ``c`` which represents the cell (or address) of a
  cube that is currently requested from the user. It is highly beneficial to use the ``CellContext`` type hint at
  all time, e.g. to benefit from code assistance. If you want to call the rule function on your own and you require
  additional parameters, then these need to be optional as the TinyOlap engine will call the function only with
  one parameter, the current cell context.

  The ``CellContext`` allows you to navigate through the data space. As shown in the example below, you
  can easily "walk" through the data space by shifting and investigate your data space by shifting to

- A returned value. This can be any datatype, but it should ideally be a generic type like float, int or string.
  As TinyOlap is all about numbers, the **float** datatype is your best friend and choice.


.. code:: python
    @rule(cube="sales", trigger=["delta"])
    def rule_profit(c: CellContext):
        return c["actual"] - c["plan"]


Simple Rules
------------

Sample of a proper rule:

.. code:: python
    def rule_average_price(c : tinyolap.context):
        quantity = c["quantity"]
        sales = c["sales"]
        # ensure both values exist or are of the expected type (cell values can be anything)
        if quantity is float and sales is float:
            if quantity != 0.0:
                return sales / quantity
            return "n.a."  # the developer decided to return some text, what is totally fine.
        return c.CONTINUE




in Python
model-driven databases starts when you define business

.. autoenum:: tinyolap.rules.RuleScope
    :members:
    :noindex:

.. autoenum:: tinyolap.rules.RuleInjectionStrategy
    :members:
    :noindex:

.. autoclass:: tinyolap.rules.Rules
    :members:
    :noindex: