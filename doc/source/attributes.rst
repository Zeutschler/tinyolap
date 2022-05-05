.. _attributes:

==========
Attributes
==========

Member attributes are optional properties of the members in a dimension.
When attributes will be added, for each attribute a specify Python type can be defined. By this you can enforce
that only specific value types will be stored in the attribute. If you do not specify a value type,
then the attribute contain any data type. The number and size of attributes is not limited.

Attributes are very handy to support easy and dynamic filtering of members and, even more useful, to enable
custom on/the fly aggregations along the attribute values. Let's say you have a **product** dimension with a
build in hierarchy for product groups and classes, and each product has certain attributes, e.g., color,
price, size, weight, manager, ingredients, date of introduction etc. You could add additional aggregations
to that dimension at any time, no problem. But it is much more convenient to add attributes to the dimension
and use these to run dynamic aggregations based on their values.

.. autoclass:: tinyolap.dimension.Attributes
    :members:
    :noindex:


.. autoclass:: tinyolap.dimension.AttributeField
    :members:
    :noindex:
