import sys

from tinyterm.colors import TermColors

sys.path.append('../')

from tinyolap.view import View, ViewWindow
import curses
import chars

class ViewGrid:
    def __init__(self, view, colors, grid_lines: bool = True, cell_width: int = 16):
        self.view: View = view
        self.window: ViewWindow = None
        self.colors: TermColors = colors
        self.screen = None

        self.grid_lines = grid_lines
        self.cell_width = cell_width

        self.cell_offset = cell_width + 1
        self.cell_height = 2 if grid_lines else 1
        self.chars = chars.SingleFrameChars()
        self.visible_rows = 0
        self.visible_cols = 0
        self.data_rows = 0
        self.data_cols = 0

        self.row_offset = 0
        self.col_offset = 0

        self.top = 0
        self.left = 0
        self.bottom = 0
        self.right = 0

        # update the TinyOlap view
        view.refresh(window=ViewWindow(0,0, self.visible_rows, self.visible_cols))

    def render(self, screen, top, left, bottom, right):
        self.screen = screen
        self.top, self.left, self.bottom, self.right = top, left, bottom, right
        self.render_gridlines(screen, top, left, bottom, right)
        self.render_view(self.window)

    def render_view(self, window=None):
        row_offset = 0
        col_offset = 0
        view = self.view
        colors = self.colors
        vfilters = view.filter_axis
        vcols = view.column_axis
        vrows = view.row_axis
        self.data_rows = self.visible_rows - (vfilters.dimensions_count + vcols.dimensions_count + 1)
        self.data_cols = self.visible_cols - vrows.dimensions_count

        # ensure that the requested data is available and fits into the window
        if not window:
            window = ViewWindow(0, 0, self.data_rows, self.data_cols)
        else:
            # ...to ensure that the requested window uses all visible cells, but is not larger than the entire view
            window.expand(self.visible_rows, self.visible_rows)
            window = window.intersect(ViewWindow(0, 0, vrows.positions_count - 1, vcols.positions_count - 1))

            if window:
                # ensure that we do not scroll out of the window. Show max. one empty row or column, then stop scrolling
                if window.rows + 1 < self.data_rows:
                    window.shift_up() #(self.data_rows - (window.rows + 1))
                    window.expand(self.visible_rows, self.visible_rows)
                    window = window.intersect(ViewWindow(0, 0, vrows.positions_count - 1, vcols.positions_count - 1))
                if window.columns + 1 < self.data_cols:
                    window.shift_left() #(self.data_cols - (window.columns + 1))
                    window.expand(self.visible_rows, self.visible_rows)
                    window = window.intersect(ViewWindow(0, 0, vrows.positions_count - 1, vcols.positions_count - 1))
        if not window:
            window = ViewWindow(0, 0, vrows.positions_count, vcols.positions_count)

        # draw filter dimensions
        for member in vfilters.positions[0]:
            self.render_cell(row_offset, 0, member.dimension.name, colors.dimension, "shifter")
            self.render_cell(row_offset, 1, member.name, colors.member, "left")
            row_offset += 1

        # draw column axis shifters
        for c in range(vcols.dimensions_count):
            grid_col = vrows.dimensions_count
            text = vcols.positions[0][c].dimension.name
            self.render_cell(row_offset, grid_col + c, text, colors.dimension, "cycler")
        row_offset += 1

        # draw row axis shifters
        for r in range(vrows.dimensions_count):
            grid_row = vcols.dimensions_count - 1
            text = vrows.positions[0][r].dimension.name
            self.render_cell(row_offset + grid_row, r, text, colors.dimension, "cycler")

        # draw column headers
        for c in range(vcols.dimensions_count):
            grid_col = vrows.dimensions_count
            for idx, view_col in enumerate(range(window.left, window.right + 1)):
                if view_col >= vcols.positions_count:
                    break
                position = vcols.positions[view_col]
                text = position[c].name
                self.render_cell(row_offset, grid_col + idx, text, colors.member, "center")
                if idx > self.data_cols:
                    break
            row_offset += 1

        # draw row headers
        for r in range(vrows.dimensions_count):
            for idx, view_row in enumerate(range(window.top, window.bottom + 1)):
                if view_row >= vrows.positions_count:
                    break
                position = vrows.positions[view_row]
                text = position[r].name
                self.render_cell(row_offset + idx, r, text, colors.member, "left")
                if idx > self.data_rows:
                    break

        # draw data
        col_offset = vrows.dimensions_count
        for idx_r, r in enumerate(range(window.top, window.bottom + 1)):
            for idx_c, c in enumerate(range(window.left, window.right + 1)):
                if r >= vrows.positions_count:
                    break
                elif c >= vcols.positions_count:
                    break
                cell = view[(c, r)]
                text = cell.formatted_value
                value = cell.value
                if value < 0:
                    self.render_cell(row_offset + idx_r, col_offset + idx_c, text, colors.number_red)
                elif text and text[0] == "+":
                    self.render_cell(row_offset + idx_r, col_offset + idx_c, text, colors.number_green)
                else:
                    self.render_cell(row_offset + idx_r, col_offset + idx_c, text, colors.number)

        # save window state
        self.window = window

    def render_cell(self, row, col, text, color=None, align=None):
        x = 1 + self.top + self.cell_height * row
        if x >= self.bottom:
            return  # invisible
        y = 1 + self.left + self.cell_offset * col
        if y >= self.right:
            return  # invisible

        text_width = len(text)
        if align:
            align = align.strip().lower()
            if align == "right":
                if text_width > self.cell_width:
                    text = "…" + text[:self.cell_width - 1]
                else:
                    text = " " * (self.cell_width - text_width) + text
            elif align == "left":
                if text_width > self.cell_width:
                    text = text[:self.cell_width - 1] + "…"
                else:
                    text = text + " " * (self.cell_width - text_width)
            elif align == "center":
                if text_width > self.cell_width:
                    text = text[:self.cell_width - 1] + "…"
                else:
                    spaces = self.cell_width - text_width
                    text = " " * (spaces // 2) + text + " " * (spaces // 2)
                    if spaces % 2 == 1:
                        text = " " + text
            elif align == "shifter":
                if text_width > self.cell_width - 2:
                    text = "←" + text[:self.cell_width - 3] + "…" + "→"
                else:
                    center_width = self.cell_width - 2
                    spaces = center_width - text_width
                    text = " " * (spaces // 2) + text + " " * (spaces // 2)
                    if spaces % 2 == 1:
                        text = " " + text
                    text = "←" + text + "→"
            elif align == "cycler":
                if text_width > self.cell_width - 2:
                    text = "↑" + text[:self.cell_width - 3] + "…" + "↓"
                else:
                    center_width = self.cell_width - 2
                    spaces = center_width - text_width
                    text = " " * (spaces // 2) + text + " " * (spaces // 2)
                    if spaces % 2 == 1:
                        text = " " + text
                    text = "↑" + text + "↓"
        else:
            if text_width > self.cell_width:
                text = "…" + text[:self.cell_width - 1]
            else:
                text = " " * (self.cell_width - text_width) + text

        overflow = self.right - (y + len(text))
        if overflow < 0:
            text = text[:len(text) + overflow]

        if color:
            self.screen.attron(color)
        self.screen.addstr(x, y, text)
        if color:
            self.screen.attroff(color)

    def render_gridlines(self, screen, top, left, bottom, right):
        """Renders a grid"""
        # calculate metrics
        width = right - left
        height = bottom - top
        max_rows = height // self.cell_height
        max_cols = width // self.cell_offset + 1

        # prepare cells
        c = self.chars
        cell_even = " " * self.cell_width + c.VERT
        cell_odd = c.HORZ * self.cell_width + c.CROSS
        cell_odd_top = c.HORZ * self.cell_width + c.HORZ_DOWN
        cell_odd_bottom = c.HORZ * self.cell_width + c.HORZ_UP

        # prepare rows
        if (width - 1) % self.cell_offset == 0:
            # special case: if the grid ends exactly at the left-most column of the window.
            #               then we need different chars at the end of each row.
            row_even = self.trim(c.VERT + (cell_even * (max_cols - 2)) + cell_even, width)

            cell_odd_last = c.HORZ * self.cell_width + c.VERT_LEFT
            cell_odd_last_top = c.HORZ * self.cell_width + c.TOP_RIGHT
            cell_odd_last_bottom = c.HORZ * self.cell_width + c.BOTTOM_RIGHT
            row_odd = self.trim(c.VERT_RIGHT + (cell_odd * (max_cols - 2)) + cell_odd_last, width)
            row_odd_top = self.trim(c.TOP_LEFT + (cell_odd_top * (max_cols - 2)) + cell_odd_last_top, width)
            row_odd_bottom = self.trim(c.BOTTOM_LEFT + (cell_odd_bottom * (max_cols - 2)) + cell_odd_last_bottom, width)
        else:
            row_even = self.trim(c.VERT + (cell_even * max_cols), width)

            row_odd = self.trim(c.VERT_RIGHT + (cell_odd * max_cols), width)
            row_odd_top = self.trim(c.TOP_LEFT + (cell_odd_top * max_cols), width)
            row_odd_bottom = self.trim(c.BOTTOM_LEFT + (cell_odd_bottom * max_cols), width)

        # draw the grid (row by row)
        screen.attron(curses.color_pair(5))
        for row in range(height):
            if row == 0:
                screen.addstr(top + row, left, row_odd_top)
            elif row % 2 == 0:
                if row == height - 1:
                    screen.addstr(top + row, left, row_odd_bottom)
                else:
                    screen.addstr(top + row, left, row_odd)
            else:
                screen.addstr(top + row, left, row_even)

        screen.attroff(curses.color_pair(5))

        self.visible_rows = max_rows
        self.visible_cols = max_cols

    @staticmethod
    def trim(text: str, width: int):
        l = len(text)
        if l > width:
            return text[:width]
        else:
            return text + " " * (width - l)
