

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

    The smallest subspace would be a single cell only, for such purposes it is recommended to use the Cell object.
    """
    pass
