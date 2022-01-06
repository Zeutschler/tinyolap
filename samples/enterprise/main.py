# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# *****************************************************************************
# TinyOlap sample database - Enterprise
# A real world data model with real world data volume for financial planning
# and reporting in a large and international enterprise.
# *****************************************************************************

from art import *
from samples.enterprise.database import create_database
from tinyolap.database import Database


def play_enterprise(db: Database, console_output=True):
    if console_output:
        tprint("TinyOlap",font="Slant")


def main():

    tprint("TinyOlap", font="Slant")

    # The following 'create_database' call wraps a best practice approach
    # to create real world = complex data models. Just follow the code to explore...
    #    1. Have a dedicated module (or class) to create and/or alter your data model
    #    2. Have a dedicated module for data import, export, maintenance and (quality) testing.
    #    3. Put additional master data into separate files (xlsx, csv, txt, json...)
    #    4. Have at least one dedicated module for your business logic. For very complex
    #       data models, you can have multiple files to separate different domains of yout logic,
    #       e.g. separate 'profit and loss calculations and KPIs' from 'HR logic'.
    db = create_database(name="TinyCorp",
                         database_directory=None,  # 'None' forces to create an in-memory database only.
                         num_legal_entities=100,
                         num_products=100,
                         num_employees=1_000)
    # Playtime!!! ʕ•́ᴥ•̀ʔっ
    play_enterprise(db, True)


if __name__ == "__main__":
    main()
