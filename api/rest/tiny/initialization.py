# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from tinyolap.server import Server
from tinyolap.database import Database
from api.rest.tiny.api import very_small_sample_db
from samples.enterprise_model.model import create_database

# set up the global server, create or add available databases
TINYOLAP_API_VERSION = "0.8.11"
server_is_initialized: bool = False
server = Server()


def setup(small_medium_large: str = "small"):
    global server, server_is_initialized

    small_medium_large =small_medium_large.strip().lower()
    if small_medium_large == "small":
        num_legal_entities = 5
        num_products = 25
        num_employees = 25
    elif small_medium_large == "medium":
        num_legal_entities = 25
        num_products = 100
        num_employees = 250
    else:
        num_legal_entities = 100
        num_products = 1000
        num_employees = 5000

    if not server_is_initialized:
        server.add_database(very_small_sample_db())
        server.add_database(
            create_database(name="TinyCorp",
                            database_directory=None,
                            num_legal_entities=num_legal_entities,
                            num_products=num_products,
                            num_employees=num_employees,
                            console_output=True)
        )
        server_is_initialized = True
