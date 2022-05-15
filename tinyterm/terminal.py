import sys
import random
import time

sys.path.append('../')

from tinyolap.database import Database
from tinyolap.view import View, ViewStatistics, ViewWindow
from tinyolap.config import Config
from samples.enterprise_model.model import create_database
import sys, os
from art import text2art
import curses
import curses.textpad, curses.panel, curses.ascii
from grid import ViewGrid
from colors import TermColors
from widgets import Widget

class TinyTerminal:
    MOUSEWHEEL_DOWN = 2097152
    MOUSEWHEEL_UP = 65536
    MOUSE_CLICK = 4
    MOUSE_DOUBLECLICK = 8
    KEY_MOUSE = 409
    KEY_UP = 259
    KEY_DOWN = 258
    KEY_LEFT = 260
    KEY_RIGHT = 261

    KEY_SHIFT_UP = 337
    KEY_SHIFT_DOWN = 336
    KEY_SHIFT_LEFT = 393
    KEY_SHIFT_RIGHT = 402

    KEY_PAGE_UP = 339
    KEY_PAGE_DOWN = 338

    def __init__(self, screen, database: Database = None, init_function = None):
        self.screen = screen
        self.init_function = init_function
        self.is_initialized = False

        self.database = database
        self.cube = None
        self.view = None
        # if database:
        #     self.cube = random.choice(database.cubes)
        #     self.view = View(self.cube, random_view=True).refresh()
        self.grid = None

        self.event = 0
        self.height = 0
        self.width = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self.button_state = 0

        self.colors = TermColors()
        self.logo = text2art("TinyOlap", font="Big").split(sep="\n")

        self.setup_terminal()
        self.show_main_screen()

    def setup_terminal(self):
        self.screen.clear()
        self.screen.erase()
        self.screen.refresh()
        curses.curs_set(1)
        self.screen.keypad(1)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    def show_main_screen(self):
        cube_list = None
        choices = {}   # self.create_widget_cube_list()
        while self.event != ord('q'):
            if self.event in choices:
                self.show_cube_view(choices[self.event])
                if self.event == ord('q'):
                    break

            self.get_state()
            if not self.is_initialized:
                self.render_title(f"TinyOlap")
                next_row = (self.height - len(self.logo) - 2) // 2
                next_row = self.render_logo(next_row)
                self.screen.refresh()
                if self.init_function:
                    if callable(self.init_function):
                        self.database = self.init_function(self.progress_callback)

                self.is_initialized = True
                cube_list, choices = self.create_widget_cube_list()
                continue
            else:
                self.render_title(f"TinyOlap | database: {self.database.name}")
                self.render_statusbar()
                next_row = (self.height - len(self.logo) - len(self.database.cubes) - 2) // 2
                next_row = self.render_logo(next_row)
                cube_list.render(next_row)
            self.wait_for_next_event()

    def progress_callback(self, progress:int, message:str):
        """Called from database initialization"""
        text = f"{float(progress)/ 100.0:.0%} database initialization - " + message
        self.render_progress_statusbar(progress, text)
        self.screen.refresh()

    def show_cube_view(self, cube):
        self.get_state()
        grid = ViewGrid(View(self.database.cubes[cube], random_view=True), self.colors)
        while self.event != ord('q') and self.event != 27:
            self.get_state()

            start = time.time()

            # process commands
            if self.event == self.KEY_MOUSE:
                if self.button_state == self.MOUSE_CLICK:
                    grid.process_mouse(self.mouse_x, self.mouse_y, "click")
                elif self.button_state == self.MOUSE_DOUBLECLICK:
                    grid.process_mouse(self.mouse_x, self.mouse_y, "doubleclick")
                elif self.button_state == self.MOUSEWHEEL_UP:
                    grid.window.shift_up()
                elif self.button_state == self.MOUSEWHEEL_DOWN:
                    grid.window.shift_down()

            elif self.event == self.KEY_SHIFT_UP:
                grid.process_shifted_keys(self.cursor_x, self.cursor_y, "up")
            elif self.event == self.KEY_SHIFT_DOWN:
                grid.process_shifted_keys(self.cursor_x, self.cursor_y, "down")
            elif self.event == self.KEY_SHIFT_LEFT:
                grid.process_shifted_keys(self.cursor_x, self.cursor_y, "left")
            elif self.event == self.KEY_SHIFT_RIGHT:
                grid.process_shifted_keys(self.cursor_x, self.cursor_y, "right")

            elif self.event == self.KEY_UP:
                grid.window.shift_up()
            elif self.event == self.KEY_DOWN:
                grid.window.shift_down()
            elif self.event == self.KEY_LEFT:
                grid.window.shift_left()
            elif self.event == self.KEY_RIGHT:
                grid.window.shift_right()

            elif self.event == self.KEY_PAGE_UP:
                grid.window.shift_up(grid.data_rows)
            elif self.event == self.KEY_PAGE_DOWN:
                grid.window.shift_down(grid.data_rows)

            elif self.event == ord('r'):
                # generate a new random report
                grid.view = View(self.database.cubes[cube], random_view=True)

            grid.render(self.screen, 1, 0, self.height-1, self.width)
            duration = time.time() - start

            self.render_title(f"TinyOlap | cube: {self.database.name}:{cube}")
            self.render_view_statusbar(duration)
            self.wait_for_next_event()

    def create_widget_cube_list(self):
        w = Widget(self.screen, self.colors)
        keys = "123456789abcdefghijklmnopqrstuvwxzy"
        choices = {}
        w.print("Please press the key for the cube to view...", self.colors.default)
        w.print("", self.colors.default)
        for idx, cube in enumerate(self.database.cubes):
            choices[ord(keys[idx:idx+1])] = cube.name
            text = f"[{keys[idx:idx+1]}] - {cube.name}"
            if cube.description:
                text += " (" + cube.description + ")"
            w.print(text, self.colors.default)
        return w, choices


    # region renderers
    def render_title(self, text):
        """Renders the title bar."""
        screen = self.screen
        screen.attron(self.colors.title)
        screen.addstr(0, 0, self.fill_to_width(text))
        screen.attroff(self.colors.title)

    def render_progress_statusbar(self, progress, text):
        """Renders the bottom status bar."""
        screen = self.screen
        text = self.fill_to_width(text, self.width - 1)
        left = text[:len(text) * progress // 100]
        right = text[len(text) * progress // 100:]

        screen.attron(self.colors.progressbar_hot)
        screen.addstr(self.height - 1, 0, left)
        screen.attroff(self.colors.progressbar_hot)
        screen.attron(self.colors.progressbar)
        screen.addstr(self.height - 1, len(left), right)
        screen.attroff(self.colors.progressbar)

    def render_generic_statusbar(self, text):
        """Renders the bottom status bar."""
        screen = self.screen
        screen.attron(self.colors.statusbar)
        screen.addstr(self.height - 1, 0, self.fill_to_width(text, self.width-1))
        screen.attroff(self.colors.statusbar)

    def render_statusbar(self):
        """Renders the bottom status bar."""
        text = f"Press 'q' to exit, 'esc' to go back | " \
               f"Pos: {self.cursor_x}, {self.cursor_y} | " \
               f"Key: {curses.keyname(self.event)} ({self.event}) | " \
               f"Mouse: {self.mouse_x}, {self.mouse_y}, " \
               f"Buttons: {self.button_state}, {bin(self.button_state)}"[:self.width - 1]
        self.render_generic_statusbar(text)

    def render_view_statusbar(self, duration: float):
        """Renders the bottom status bar for a view."""
        text = f"Press 'r' for random report, 'esc' to go back | {int(duration * 1_000):n} ms | " \
               f"Pos: {self.cursor_x}, {self.cursor_y} | " \
               f"Key: {curses.keyname(self.event)} ({self.event}) | " \
               f"Mouse: {self.mouse_x}, {self.mouse_y}, " \
               f"Buttons: {self.button_state}, {bin(self.button_state)}"[:self.width - 1]
        self.render_generic_statusbar(text)

    def render_logo(self, first_row = -1) -> int:
        """Renders the TinyOlap logo."""
        screen = self.screen

        logo_height = len(self.logo)
        logo_width = len(self.logo[0])
        if first_row == -1:
            first_row = (self.height - logo_height) // 2
        next_row = first_row
        draw_logo = (self.height - logo_height - 3) > 0
        if draw_logo:
            overflow_x = self.width - logo_width

            screen.attron(self.colors.logo_light)
            for row, text in zip(range(first_row, first_row + logo_height), self.logo):
                if overflow_x < 0:
                    if overflow_x % 2 == 0:  # even
                        strip = abs(overflow_x) // 2
                        text = text[strip: len(text)-strip]
                    else:  # odd
                        strip_left = abs(overflow_x) // 2
                        strip_right = strip_left + 1
                        text = text[strip_left: len(text)-strip_right]
                col = (self.width - len(text)) // 2
                screen.addstr(row, col, text)
            screen.attroff(self.colors.logo_light)

            # show version info
            next_row = first_row + logo_height
            version_info = f"version: {Config.VERSION}"[:self.width - 1]
            col = (self.width - (logo_width - 6)) // 2
            if col > 0 and (col + len(version_info)) < self.width:
                screen.attron(self.colors.logo_light)
                screen.addstr(next_row - 3, col, version_info)
                screen.attroff(self.colors.logo_light)
        else:
            screen.attron(self.colors.logo_light)
            next_row = self.height // 2
            version_info = f"TinyOlap version {Config.VERSION}"[:self.width - 1]
            screen.addstr(next_row, (self.width - len(version_info)) // 2, version_info)
            screen.attroff(self.colors.logo_light)
        return next_row + 1
    # endregion

    # region Window management
    def get_state(self):
        self.get_screen()
        self.get_mouse()
        self.get_cursor()

    def wait_for_next_event(self):
        self.screen.move(self.cursor_y, self.cursor_x)
        self.screen.refresh()
        self.event = self.screen.getch()

    def get_cursor(self):
        # evaluate cursor keys
        x = self.cursor_x
        y = self.cursor_y
        if self.event == curses.KEY_DOWN:
            y = y + 1
        elif self.event == curses.KEY_UP:
            y = y - 1
        elif self.event == curses.KEY_RIGHT:
            x = x + 1
        elif self.event == curses.KEY_LEFT:
            x = x - 1
        x = max(0, x)
        x = min(self.width - 1, x)
        y = max(0, y)
        y = min(self.height - 1, y)
        self.cursor_x = x
        self.cursor_y = y

    def get_screen(self):
        """Resets screen and get screen dimensions."""
        self.screen.erase()
        self.height, self.width = self.screen.getmaxyx()

    def get_mouse(self):
        """Returns the current mouse position."""
        try:
            _, self.mouse_x, self.mouse_y, _, self.button_state = curses.getmouse()
        except Exception:
            self.mouse_x = "?"
            self.mouse_y = "?"
            self.button_state = 0
    # endregion

    # region helpers
    def fill_to_width(self, text: str, width: int = -1):
        if width == -1:
            width = self.width
        l = len(text)
        if l > width:
            return text[:width]
        else:
            return (text + " " * (width - l))[:width]

    def trim(self, text: str, width: int = -1):
        if width == -1:
            width = self.width
        return text[:width]
    # endregion