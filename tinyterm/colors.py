import curses


class TermColors:
    def __init__(self, schema=None):
        curses.start_color()
        curses.use_default_colors()

        # create color names
        self.default = None
        self.title = None
        self.statusbar = None
        self.grid = None
        self.logo_light = None
        self.logo = None
        self.logo_dark = None

        self.label = None
        self.dimension = None
        self.member = None
        self.arrow = None
        self.number = None
        self.number_red = None
        self.number_green = None

        # name : (number, fore-color, back-color)
        if schema == "tiny":
            default_colors = {}
        else:
            default_colors = \
                {"default": (1, 15, 0),     # white on black
                 "disabled": (2, 247, 0),   # light-grey on black
                 "title": (3, 0, 33),       # white on Tiny-blue
                 "statusbar": (4, 248, 8),  # white on dark-grey
                 "grid": (5, 239, 0),       # dark-grey on black
                 "logo_light": (6, 45, 0),  # Tiny-cyan on black
                 "logo": (7, 33, 0),        # Tiny-blue on black
                 "logo_dark": (8, 20, 0),   # Tiny-dark-blue on black

                 "label": (9, 243, 0),          # grey on black
                 "dimension": (10, 208, 0),     # orange on black
                 "member": (11, 15, 236),        # white on dark-blue
                 "arrow": (12, 208, 0),         # orange on black
                 "number": (13, 15, 0),         # white on black
                 "number_red": (14, 196, 0),    # red on black
                 "number_green": (15, 40, 0),   # green on black
                 }
        # create color instances
        for name, v in default_colors.items():
            if not (v[1] is None and v[2] is None):
                curses.init_pair(v[0], v[1], v[2])
            self.__setattr__(name, curses.color_pair(v[0]))

    # def render_colors(self):
    #     curses.start_color()
    #     curses.use_default_colors()
    #     z = 0
    #     for i in range(0, curses.COLORS):
    #         z += 1
    #         # curses.init_pair(z, i, 0)
    #         # curses.init_pair(z, 0, i)
    #         curses.init_pair(z, 15, i)
    #
    #     try:
    #         for i in range(0, 256):
    #             stdscr.addstr(f" {i:0=3d} ", curses.color_pair(i))
    #     except Exception as err:
    #         if err is curses.ERR:
    #             # End of screen reached
    #             pass
    #         else:
    #             raise RuntimeError(f"Something went wrong. {str(err)}")


def main(stdscr):
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
