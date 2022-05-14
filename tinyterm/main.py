import sys, os
sys.path.append('../')

from samples.enterprise_model.model import create_database
import curses
from terminal import TinyTerminal


def draw_menu(screen):
    database = create_database(name="TinyCorp", database_directory=None,
                                    num_legal_entities=100, num_products=50,
                                    num_employees=50, console_output=False,
                                    caching=True)
    term = TinyTerminal(screen, database=database)


def main():
    # set shorter delay for ESC key, default is 1000ms, we use 25ms
    os.environ.setdefault('ESCDELAY', '25')
    curses.wrapper(draw_menu)


if __name__ == "__main__":
    main()