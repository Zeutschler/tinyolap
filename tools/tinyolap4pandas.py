import pandas as pd

import tinyolap.cube
from tinyolap.database import Database
from tinyolap.cube import Cube


class TinyOlap4Pandas:
    """
    Methods to convert Pandas DataFrames to TinyOlap Databases or Cubes, and vice versa.
    """

    @staticmethod
    def df_to_tiny_cube(df: pd.DataFrame, database_name: str = "tiny", cube_name: str = "data") -> Database:
        """
        Converts a Pandas DataFrame to a TinyOlap cube. This is more convenient than to call
        'df_to_tiny_database' which returns a database, and you need to access the cube in a separate step.
        :param df: The Pandas DataFrame to be converted.
        :param database_name: (optional) the name of the TinyOlap Database to be created. Default name is 'tiny'.
        :param cube_name: (optional) the name of the TinyOlap Cube to be created. Default name is 'data'.
        :return: A TinyOlap cube containing the data of the Pandas DataFrame.
        """
        return TinyOlap4Pandas.df_to_tiny_database(df, database_name, cube_name).cubes[cube_name]

    @staticmethod
    def df_to_tiny_database(df: pd.DataFrame, database_name: str = "tiny", cube_name: str = "data") -> Database:
        """
        Converts a Pandas DataFrame to a TinyOlap cube. This is more convenient than to call
        'df_to_tiny_database' which returns a database, and you need to access the cube in a separate step.
        :param df: The Pandas DataFrame to be converted.
        :param database_name: (optional) the name of the TinyOlap Database to be created. Default name is 'tiny'.
        :param cube_name: (optional) the name of the TinyOlap Cube to be created. Default name is 'data'.
        :return: A TinyOlap cube containing the data of the Pandas DataFrame.
        """
        raise NotImplementedError()

    @staticmethod
    def tiny_cube_to_df(cube: Cube) -> pd.DataFrame:
        """
        Converts a TinyOlap Cube into a Pandas DataFrame.
        :param cube: The TinyOlap Cube to be converted.
        :return: A Pandas DataFrame containing the data of the cube.
        """
        raise NotImplementedError()

    @staticmethod
    def tiny_database_add_df(database: Database, df: pd.DataFrame, cube_name: str) -> Cube:
        """
        Adds a new Cube to an existing TinyOlap database. Please note, that new
        dimensions will be added to the cube named '[cube_name]_[df_col_names]'.
        :param database: The target TinyOlap database.
        :param df: The Pandas DataFrame to be added.
        :param cube_name: Name of the TinyOlap Cube to be added.
        :return: The newly added Cube.
        """
        raise NotImplementedError()






