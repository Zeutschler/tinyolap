# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import sys, os

sys.path.append('../')

from samples.enterprise_model.model import create_database
import curses
from terminal import TinyTerminal

num_legal_entities = 25
num_products = 200
num_employees = 500


def initialize_database(callback_function):
    database = create_database(name="TinyCorp", database_directory=None,
                               num_legal_entities=num_legal_entities,
                               num_products=num_products,
                               num_employees=num_employees, console_output=False,
                               caching=True, callback=callback_function)
    return database


def draw_menu(screen):
    term = TinyTerminal(screen, init_function=initialize_database)


def main():
    # set shorter delay for ESC key, default is 1000ms, we use 25ms
    os.environ.setdefault('ESCDELAY', '25')
    curses.wrapper(draw_menu)


if __name__ == "__main__":
    main()
