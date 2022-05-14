import curses

from tinyterm.colors import TermColors


class Widget:

    def __init__(self, screen,colors, width: int = -1, height: int = -1):
        self.screen = screen
        self.colors: TermColors = colors

        self.width = width
        self.height = height
        self.rows = []

    def clear(self):
        """Clears the widget area."""
        self.rows = []

    def print(self, text: str, color = None):
        self.rows.append((text, color,))

    def render(self, top: int = -1, left: int = -1):
        screen = self.screen
        height = self.height
        width = self.width

        # adjust width and height, if required
        if width == -1:  # auto width
            for text, color in self.rows:
                if len(text) > width:
                    width = len(text)
        if height == -1:  # auto height
            height = len(self.rows)
        max_height, max_width = screen.getmaxyx()

        if top < 0:  # vertical centered
            top = (max_height - height) // 2
            if top < 0:
                first_row = abs(top) // 2
                last_row = height - abs(top) // 2
                if abs(top) % 2 == 1:
                    last_row -= 1
                top = 0
            else:
                first_row = 0
                last_row = height
        else:
            if top > max_height:
                return  # invisible area
            if top + height > max_height:
                first_row = 0
                last_row = height + (max_height - (top + height))
            else:
                first_row = 0
                last_row = height

        if left < 0:  # horizontal centered
            left = (max_width - width) // 2
            if left < 0:
                first_col = 0
                last_col = min(max_width, width - first_col)
                if abs(left) % 2 == 1:
                    last_col -= 1
                left = 0
            else:
                first_col = 0
                last_col = width
        else:
            if left > max_width:
                return  # invisible area
            if left + width > max_width:
                first_col = 0
                last_col = (left + width) - max_width
            else:
                first_col = 0
                last_col = width

        # render content
        for row, line in enumerate(self.rows):
            if first_row <= row < last_row:
                text, color = line
                if color:
                    screen.attron(color)
                text_width = len(text)
                if text_width > last_col:
                    text = text[:last_col - 1] + "…"
                text = text[first_col:last_col]
                screen.addstr(top + row, left + first_col, text)
                if color:
                    screen.attroff(color)
                if row >= height:
                    break
            row += 1
            if row > last_row:
                break
