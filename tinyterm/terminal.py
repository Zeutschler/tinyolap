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
    KEY_PAGE_UP = 339
    KEY_PAGE_DOWN = 338

    def __init__(self, screen, database: Database = None):
        self.screen = screen
        self.database = database
        self.cube = random.choice(database.cubes)
        self.view = View(self.cube, random_view=True).refresh()
        self.grid = None
        self.colors = TermColors()
        self.event = 0
        self.height = 0
        self.width = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self.button_state = 0
        self.logo = text2art("TinyOlap", font="Big").split(sep="\n")
        self.initialize()
        self.show_main_screen()

    def initialize(self):
        # Clear and refresh the screen for a blank canvas
        self.screen.clear()
        self.screen.erase()
        self.screen.refresh()
        curses.curs_set(0)
        self.screen.keypad(1)
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    def show_main_screen(self):
        cube_list, choices = self.create_widget_cube_list()
        while self.event != ord('q'):
            if self.event in choices:
                self.show_cube_view(choices[self.event])
                if self.event == ord('q'):
                    break


            self.get_state()
            self.render_title(f"TinyOlap | database: {self.database.name}")
            next_row = (self.height - len(self.logo) - len(self.database.cubes) - 2) // 2
            next_row = self.render_logo(next_row)
            cube_list.render(next_row)
            self.render_statusbar()
            self.wait_for_next_event()

    def show_cube_view(self, cube):
        self.get_state()
        grid = ViewGrid(View(self.database.cubes[cube], random_view=True), self.colors)
        while self.event != ord('q') and self.event != 27:
            self.get_state()

            start = time.time()

            # process commands
            if self.event == self.KEY_MOUSE:
                if self.button_state == self.MOUSE_CLICK:
                    pass
                elif self.button_state == self.MOUSE_DOUBLECLICK:
                    pass
                elif self.button_state == self.MOUSEWHEEL_UP:
                    grid.window.shift_up()
                elif self.button_state == self.MOUSEWHEEL_DOWN:
                    grid.window.shift_down()
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
                grid.view = View(self.database.cubes[cube], random_view=True) #.refresh(window=ViewWindow(0,0, self.width//14, self.height//2))


            grid.render(self.screen, 1, 0, self.height-1, self.width)

            duration = time.time() - start

            self.render_title(f"TinyOlap | cube: {self.database.name}:{cube}")
            self.render_view_statusbar(duration)
            self.wait_for_next_event()

    def show_browser(self):
        pass

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

    def render_title(self, text):
        """Renders the title bar."""
        screen = self.screen
        screen.attron(self.colors.title)
        screen.addstr(0, 0, self.fill_to_width(text))
        screen.attroff(self.colors.title)

    def render_statusbar(self):
        """Renders the bottom status bar."""
        screen = self.screen
        text = f"Press 'q' to exit, 'esc' to go back | STATUS BAR | " \
               f"Pos: {self.cursor_x}, {self.cursor_y} | " \
               f"Key: {curses.keyname(self.event)} ({self.event}) | " \
               f"Mouse: {self.mouse_x}, {self.mouse_y}, " \
               f"Buttons: {self.button_state}, {bin(self.button_state)}"[:self.width - 1]
        screen.attron(self.colors.statusbar)
        screen.addstr(self.height - 1, 0, self.fill_to_width(text, self.width-1))
        screen.attroff(self.colors.statusbar)

    def render_view_statusbar(self, duration):
        """Renders the bottom status bar for a view."""
        screen = self.screen
        text = f"Press 'q' to exit, 'esc' to go back | {duration * 1000 :,.0f} ms | " \
               f"Pos: {self.cursor_x}, {self.cursor_y} | " \
               f"Key: {curses.keyname(self.event)} ({self.event}) | " \
               f"Mouse: {self.mouse_x}, {self.mouse_y}, " \
               f"Buttons: {self.button_state}, {bin(self.button_state)}"[:self.width - 1]
        screen.attron(self.colors.statusbar)
        screen.addstr(self.height - 1, 0, self.fill_to_width(text, self.width-1))
        screen.attroff(self.colors.statusbar)

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


