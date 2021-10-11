

class Area:
    """
    An Area represents a subspace of a cube. Areas are intended be used for mass operations on cube cells.
    The following example should explain the basic concept:

    .. code:: python

        area = cube.area("Jan", "2023", "Plan")
        # clears all data for months='Jan', years='2023' and datatype='Plan' over all other dimensions.
        area.clear()

        # Copies all data from 'Actual', '2022', increases all values by 15% and writes them to the 'Plan' for '2023'.
        # Info: All data in the target area will be deleted before hand.
        # Info: Depending on the amount of data to be copied, such operations may take some time (a few seconds).
        cube.area("Plan", "2023") = cube.area("Actual", "2022") * 1,15

    The smallest possible subspace would be a single cube cell.
    For such purposes it is recommended to use the Cell object.
    """

    def __init__(self, cube, args):
        """
        Initializes a new data area for a specific cube.
        :param cube: The cube to create the data area for.
        :param args: The member specification for the data area.
        """
        pass

    def items(self):
        """
        Generator to loop over existing items of the data area.
        Returns nested tuples in the form ((dim_member1, ... , dim_memberN), value).
        """
        pass

    def addresses(self):
        """
        Generator to loop over existing addresses of the data area.
        Returns tuples in the form (dim_member1, ... , dim_memberN).
        """
        pass

    def clear(self):
        """
        Clears the data area. All cells holding values will be removed from the cube.
        """
        return NotImplemented

    def multiply(self, value: float):
        """
        Multiplies all cells holding numeric values with a certain value.
        :type value: The factor to multiply all cells holding numeric values with.
        """
        return NotImplemented

    def increment(self, value: float):
        """
        Increments all cells holding numeric values by a certain value.
        :type value: The value to increment all cells holding numeric values by.
        """

    def min(self):
        """
        Returns the minimum value of all numeric values in the data area.
        """
        return NotImplemented

    def max(self):
        """
        Returns the maximum value of all numeric values in the data area.
        """
        return NotImplemented

    def avg(self):
        """
        Returns the average of all numeric values in the data area.
        """
        return NotImplemented

    def sum(self):
        """
        Returns the sum of all numeric values in the data area.
        """
        return NotImplemented

    def to_json(self, compact: bool = True):
        """
        Returns a data area as a json string, including the definition of the area
        and all base level cell data from that area. For larger data areas it is
        recommended to set parameter ``compact`` to ``True`` (the default value).
        This reduces the size of the returned json string by factor 2 to 10.

        The json returned by this method will identical to calling ``json.dumps(area.to_dict())`` .

        This function is intended to be used for custom persistence.
        If you just want to temporarily keep data (e.g. to undo certain changes),
        in memory, then consider to use method ``to_dict()`` for better performance
        instead.

        :param compact: Identifies is the data area should be compacted.
        """
        return NotImplemented

    def from_json(self, json: str, validate: bool = False) -> bool:
        """
        Reads a data area from a json string, clears the data area and
        writes (imports) all values contained in the data area definition into the cube.

        :param json: A json string containing the data area definition.
        :param validate: If set to ``True`` , the data area will be validated before importing.
        By this you can ensure that all values of the data area can be written to the cube.
        If at least one value of the data area can not be written to the cube, then ```from_json()``
        will stop and return ``False`` , otherwise the method will continue and start to write
        (import) values to the cube.
        :return Returns ``True``if the import was successful, ``False``otherwise.
        """
        return NotImplemented

    def to_dict(self, compact: bool = True):
        """
        Returns a data area as a Python ``dict`` object. For larger data areas it is
        recommended to set parameter ``compact`` to ``True`` (the default value).
        This reduces the memory footprint of the returned dict by factor 2 to 10.

        :param compact: Identifies is the data area should be compacted.
        """
        return NotImplemented

    def from_dict(self, area_dict: dict, validate: bool = False) -> bool:
        """
        Reads a data area from a Python dict object, clears the data area and
        writes (imports) all values contained in the data area definition into the cube.

        :param area_dict: A Python dict object containing the data area definition.
        :param validate: If set to ``True`` , the data area will be validated before importing.
        By this you can ensure that all values of the data area can be written to the cube.
        If at least one value of the data area can not be written to the cube, then ```from_dict()``
        will stop and return ``False`` , otherwise the method will continue and start to write
        (import) values to the cube.
        :return Returns ``True``if the import was successful, ``False``otherwise.
        """
        return NotImplemented

    # region operator overloading for numerical operations
    def __add__(self, other):  # + operator
        return self + other

    def __iadd__(self, other):  # += operator
        return self + other

    def __radd__(self, other):  # + operator
        return other + self

    def __sub__(self, other):  # - operator
        return self - other

    def __isub__(self, other):  # -= operator
        return self - other

    def __rsub__(self, other):  # - operator
        return other - self

    def __mul__(self, other):  # * operator
        return self * other

    def __imul__(self, other):  # *= operator
        return self * other

    def __rmul__(self, other):  # * operator
        return other * self

    def __floordiv__(self, other):  # // operator (returns an integer)
        return self // other

    def __ifloordiv__(self, other):  # //= operator (returns an integer)
        return self // other

    def __rfloordiv__(self, other):  # // operator (returns an integer)
        return other // self
    # endregion
