import itertools
import json
import math
import random
import uuid
from datetime import datetime
import time
from typing import Iterable, List
from dataclasses import dataclass

from tinyolap.config import Config
from tinyolap.dimension import Dimension
from tinyolap.member import Member, MemberList
from tinyolap.cube import Cube


@dataclass
class ViewCell:
    value: float = 0.0
    formatted_value: str = ""


@dataclass
class ViewStatistics:
    last_refresh: datetime = datetime.min
    refresh_duration: float = 0.0
    cells_count: int = 0
    rows: int = 0
    columns: int = 0
    row_dimensions: int = 0
    column_dimensions: int = 0
    executed_rules: int = 0
    executed_cell_requests: int = 0
    executed_cell_aggregations: int = 0

    def to_dict(self) -> dict:
        return {
            'lastRefresh': str(self.last_refresh.isoformat()),
            'refreshDuration': self.refresh_duration,
            'cellsCount': self.cells_count,
            'rowsCount': self.rows,
            'columnsCount': self.columns,
            'rowDimensionsCount': self.row_dimensions,
            'columnDimensionsCount': self.column_dimensions,
            'executedRules': self.executed_rules,
            'executedCellRequests': self.executed_cell_requests,
            'executedCellAggregations': self.executed_cell_aggregations
        }


class ViewAxisPosition:
    def __init__(self, view, axis, members: tuple[Member]):
        self._view = view
        self._axis = axis
        self._members = members

    def __len__(self):
        return len(self._members)

    def __iter__(self):
        return self._members.__iter__()

    def __getitem__(self, item: int) -> Member:
        return self._members[item]

    def __str__(self):
        return f"ViewAxisPos['{[member for member in self._members]}']"

    def __repr__(self):
        return f"ViewAxisPos['{[member for member in self._members]}']"

    @property
    def dimensions_count(self):
        """Returns the number of position on the axis."""
        return len(self._members)


class ViewAxis(Iterable[ViewAxisPosition]):

    def __init__(self, view, idx, dimensions, member_lists):
        self._view = view
        self._positions: tuple[ViewAxisPosition] = tuple()

        if type(dimensions) is tuple and type(member_lists) is tuple:
            self._dimensions: tuple[Dimension] = dimensions
            self._dim_members: tuple[MemberList] = member_lists
            self._dim_idx: tuple[int] = idx
        else:
            self._dimensions: tuple[Dimension] = (dimensions,)
            self._dim_members: tuple[MemberList] = (member_lists,)
            self._dim_idx: tuple[int] = (idx,)

        self._dim_count = len(self._dimensions)
        self._members_counts = tuple([len(members) for members in self._dim_members])

        # fill positions
        positions = []
        for position in itertools.product(*self._dim_members):
            positions.append(ViewAxisPosition(self._view, self, position))
        self._positions = tuple(positions)
        self._positions_count = len(self._positions)

    def __iter__(self):
        return self._positions.__iter__()

    def __getitem__(self, index: int) -> ViewAxisPosition:
        return self._positions[index]

    def __len__(self):
        """returns the number of positions"""
        return len(self._positions)

    def __str__(self):
        return f"Axis[{', '.join([dim.name + f'({len(members)})' for dim, members in zip(self._dimensions, self._dim_members)])}]"

    def __repr__(self):
        return self.__str__()

    @property
    def positions_count(self):
        """Returns the number of position on the axis."""
        return len(self._positions)

    @property
    def dimensions_count(self):
        """Returns the number of dimensions on the axis."""
        return len(self._dimensions)

    @property
    def dimensions(self) -> tuple[Dimension]:
        """Returns the number of position on the axis."""
        return self._dimensions

    @property
    def positions(self) -> tuple[ViewAxisPosition]:
        """Returns the number of position on the axis."""
        return self._positions

    def to_dict(self) -> dict:
        """Converts the view axis into a serializable Python dictionary."""
        """FOR INTERNAL USE! Converts the contents of the attribute field to a dict."""
        return {"dimensions": [
            {"name": dim.name, "ordinal": ordinal}
            for ordinal, dim in enumerate(self._dimensions)
        ],
            "positions": [
                {"row": row, "members": [
                    {"name": member.name, "level": member.level,
                     "root": member.is_root} for member in position
                ]} for row, position in enumerate(self._positions)
            ],
        }


class View:
    """
    Represents a view to a cube. Used for reporting purposes. Views manage, optimize
    and provide the client side access to data from a TinyOlap cube.
    """

    # todo: drilldown path
    # todo: drilldowns ermöglichen
    # todo: json output fUr clients

    def __init__(self, cube: Cube,
                 view_definition=None,
                 zero_suppression_on_rows: bool = False,
                 zero_suppression_on_columns: bool = False,
                 uid=None,
                 random_view: bool = False,
                 use_first_root_members_for_filters: bool = False):
        """
        Initializes a new view for the given cube.
        :param cube: The Cube to create a view for.
        :param view_definition: (optional) a valid view definition. If no view definition then
        a default view definition, based on the cubes structure, will be created.
        :param zero_suppression_on_rows: Identifies is zero suppression should be applied to the rows of the view.
        :param zero_suppression_on_columns: Identifies is zero suppression should be applied to the columns of the view.
        :param uid: A uid of the view object. Useful for client/server interaction, persistence and state management.
        :param random_view: Flag to force the creation of a random view, instead of the default view, upon
            the given cube. Only valid for the case that no view definition is defined.
        :param use_first_root_members_for_filters: Flag to force to set the first root member for all filter dimensions.
            This applies to both random views and the default view.
        """
        self._cube: Cube = cube
        self._def = view_definition
        self._row_zero: bool = zero_suppression_on_rows
        self._col_zero: bool = zero_suppression_on_columns
        self._cells = []
        self._title: str = "TinyOlap View"
        self._description: str = ""
        self._uid: str = str(uid) if uid else str(uuid.uuid4())
        self._random_view: bool = random_view
        self._use_first_root_members_for_filters = use_first_root_members_for_filters

        self._statistics: ViewStatistics = ViewStatistics()
        if not self._def:
            self._create_default_view_definition()
        else:
            self._filter_axis: ViewAxis = ...
            self._row_axis: ViewAxis = ...
            self._col_axis: ViewAxis = ...

        self._validate()

    @property
    def cube(self) -> Cube:
        """Returns the cube of the view."""
        return self._cube

    @property
    def definition(self) -> dict:
        """Returns the cube of the view."""
        return self._def

    @property
    def uid(self) -> str:
        """Returns the uid of the view. Useful for client/server interaction, persistence and state management."""
        return self._uid

    @property
    def title(self) -> str:
        """Returns the title of the view."""
        return self._title

    @title.setter
    def title(self, value: str):
        """Sets the title of the view."""
        self._title = value

    @property
    def description(self) -> str:
        """Returns the description of the view."""
        return self._description

    @description.setter
    def description(self, value: str):
        """Sets the description of the view."""
        self._description = value

    @property
    def statistics(self) -> ViewStatistics:
        """Returns the statistic information about the view."""
        return self._statistics

    @property
    def zero_suppression_on_rows(self) -> bool:
        """Returns the zero-suppression setting for the rows of the view."""
        return self._row_zero

    @zero_suppression_on_rows.setter
    def zero_suppression_on_rows(self, value: bool):
        """Sets the zero-suppression setting for the rows of the view."""
        # todo: refresh the view when changing zero suppression
        self._row_zero = value

    @property
    def zero_suppression_on_columns(self) -> bool:
        """Returns the zero-suppression setting for the columns of the view."""
        return self._col_zero

    @zero_suppression_on_columns.setter
    def zero_suppression_on_columns(self, value: bool):
        """Sets the zero-suppression setting for the columns of the view."""
        # todo: refresh the view when changing zero suppression
        self._col_zero = value

    @property
    def use_first_root_members_for_filters(self) -> bool:
        """Returns if the first root member will be set for all filter dimensions in random or default views."""
        return self._use_first_root_members_for_filters

    @use_first_root_members_for_filters.setter
    def use_first_root_members_for_filters(self, value: bool):
        """Sets if the first root member should be set for all filter dimensions in random or default views."""
        self._use_first_root_members_for_filters = value

    @property
    def filter_axis(self):
        """Returns the filter axis of the view, containing the filter settings of the view."""
        return self._filter_axis

    @property
    def row_axis(self):
        """Returns the row axis, containing the member sets defined for the rows of the view."""
        return self._row_axis

    @property
    def column_axis(self):
        """Returns the column axis, containing the member sets defined for the columns of the view."""
        return self._col_axis

    def __getitem__(self, coordinates) -> ViewCell:
        """
        Retrieves a single view cell from the view using its coordinates.

        .. code:: python

            view = View(cube)
            # return the cell at the ordinal position 0
            cell = view[0]
            # return the cell at the row/column position (1, 1)
            cell = view[1, 1]
            # return the cell at the row position ("North", "Cars") and
            # the column position "Jan".
            cell = view["North", "Cars", "Jan"]

        Coordinates are a value or an array of values that uniquely specify
        a data cell with the rows and columns of the view.

        Coordinates can be one of the following:

            * An array of position numbers
            * An array of member names
            * The ordinal position

        :param coordinates: The position to be returned
        :return: A view cell object
        """

        if type(coordinates) is int:
            # ordinal position
            col = coordinates % self._col_axis._positions_count
            row = int(math.floor(coordinates / self._col_axis._positions_count))
        elif len(coordinates) == 2 and type(coordinates[0]) is int:
            col = coordinates[0]
            row = coordinates[1]
        else:
            col = 0
            row = 0
            raise NotImplementedError()

        # collect address by index (not by name, by index is much faster)
        idx_address = [0] * self._cube.dimensions_count
        axis = self._filter_axis
        super_level = 0
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[0][i].index
            super_level += axis.positions[0][i].level
        axis = self._row_axis
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[row][i].index
            super_level += axis.positions[row][i].level
        axis = self._col_axis
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[col][i].index
            super_level += axis.positions[col][i].level

        value = self.cube._get((super_level, tuple(idx_address),))
        return ViewCell(value, str(value))

    def __setitem__(self, coordinates, value):
        """
        Sets the value for a single view cell from the view using its coordinates.
        This method should be used by clients to write data entered by a user into the cube.

        Coordinates are a value or an array of values that uniquely specify
        a data cell with the rows and columns of the view.

        Coordinates can be one of the following:

            * An array of position numbers
            * An array of member names
            * The ordinal position

        :param coordinates: The position to be accessed.
        :param value: The value to be written.
        :return: A view cell object
        """
        return ViewCell()

    def __repr__(self):
        return f"View['{self._cube.name}'] with " \
               f"[{self._row_axis}] " \
               f"on rows, " \
               f"[{self._col_axis}] " \
               f"on columns and " \
               f"[{self._filter_axis}] " \
               f"as filters."

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        return self._col_axis.positions_count * self._row_axis.positions_count

    def cell(self, coordinates) -> ViewCell:
        """
        Retrieves a single view cell from the view using its coordinates.
        It is recommended to use the build-in __getitem__ method.

        .. code:: python

            view = View(cube)
            # return the cell at the ordinal position 0
            cell = view[0]
            # return the cell at the row/column position (1, 1)
            cell = view[1, 1]
            # return the cell at the row position ("North", "Cars") and
            # the column position "Jan".
            cell = view["North", "Cars", "Jan"]

        Coordinates are a value or an array of values that uniquely specify
        a data cell with the rows and columns of the view.

        Coordinates can be one of the following:

            * An array of position numbers
            * An array of member names
            * The ordinal position

        :param coordinates: The position to be returned
        :return: A view cell object
        """
        return self.__getitem__(coordinates)

    def _validate(self) -> bool:
        """Validates the view definition."""
        return False

    def refresh(self):
        """Refreshes (updates) the view."""

        # prepare statistics
        stat = self._statistics
        stat.refresh_duration = time.time()
        stat.executed_cell_requests = self._cube.counter_cell_requests
        stat.executed_cell_aggregations = self._cube.counter_aggregations
        stat.executed_rules = self._cube.counter_rule_requests

        # refresh filter axis first to create a FactTableRowSet
        cells = []
        filter_level = 0
        idx_address = [0] * self._cube.dimensions_count
        axis = self._filter_axis
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[0][i].index
            filter_level += axis.positions[0][i].level
        row_set = self._cube._facts.create_row_set(idx_address)

        rows = self._row_axis
        cols = self._col_axis
        for row in range(rows.positions_count):
            super_level = filter_level
            for i in range(rows._dim_count):
                idx_address[rows._dim_idx[i]] = rows.positions[row][i].index
                super_level += rows.positions[row][i].level

            for col in range(cols.positions_count):
                for i in range(cols._dim_count):
                    idx_address[cols._dim_idx[i]] = cols.positions[col][i].index
                    super_level += cols.positions[col][i].level

                value = self._cube._get((super_level, tuple(idx_address), ), row_set=row_set)

                if type(value) is not float:  # e.g.  for Rule Errors
                    value = str(value)

                view_cell = ViewCell(value, str(value))
                if col == 0:
                    cells.append([view_cell, ])
                else:
                    cells[row].append(view_cell)
        self._cells = cells

        # update statistics
        stat.last_refresh = datetime.now()
        stat.refresh_duration = round(time.time() - stat.refresh_duration, 6)
        stat.executed_cell_requests = self._cube.counter_cell_requests - stat.executed_cell_requests
        stat.executed_cell_aggregations = self._cube.counter_aggregations - stat.executed_cell_aggregations
        stat.executed_rules = self._cube.counter_rule_requests - stat.executed_rules
        stat.rows = rows.positions_count
        stat.columns = cols.positions_count
        stat.cells_count = stat.rows * stat.columns
        stat.row_dimensions = rows._dim_count
        stat.column_dimensions = cols._dim_count

        return self

    def _create_default_view_definition(self):
        """Creates a default view definition.

        The last dimension of the cube will be placed in the column axis of the view,
        the previous last (if such exists) in the row axis and all remaining dimensions
        will be placed in the filter axis"""

        # todo:  missing random implementation

        dimensions = self._cube.dimensions
        ordinal = list(range(len(dimensions)))
        if self._random_view:
            random.shuffle(ordinal)
        remaining = len(dimensions)

        # set up column axis
        if remaining > 0:
            idx = remaining - 1
            self._col_axis = ViewAxis(self, idx=ordinal[idx], dimensions=dimensions[ordinal[idx]],
                                      member_lists=dimensions[ordinal[idx]].members)
            remaining -= 1

        # set up row axis
        if remaining > 0:
            idx = remaining - 1
            self._row_axis = ViewAxis(self, idx=ordinal[idx], dimensions=dimensions[ordinal[idx]],
                                      member_lists=dimensions[ordinal[idx]].members)
            remaining -= 1

        # set up filter axis
        if remaining > 0:
            if self._use_first_root_members_for_filters:
                self._filter_axis = ViewAxis(self,
                                         idx=tuple([ordinal[idx] for idx in range(remaining)]),
                                         dimensions=tuple([dimensions[ordinal[idx]] for idx in range(remaining)]),
                                         member_lists=tuple(
                                             [MemberList(dimension=dimensions[ordinal[idx]],
                                                         members=dimensions[ordinal[idx]].root_members[0])
                                              for idx in range(remaining)]))
            else:
                self._filter_axis = ViewAxis(self,
                                         idx=tuple([ordinal[idx] for idx in range(remaining)]),
                                         dimensions=tuple([dimensions[ordinal[idx]] for idx in range(remaining)]),
                                         member_lists=tuple(
                                             [MemberList(dimension=dimensions[ordinal[idx]],
                                                         members=dimensions[ordinal[idx]].members[0])
                                              for idx in range(remaining)]))

    def as_console_output(self, hide_zeros: bool = True) -> str:
        """Renders the view suitable for console output. The output contains
        control characters and color definitions and is therefore not suitable
        for other use cases."""
        text = "\n"
        cell_width = 14
        row_header_width = 16

        row_dims = self._row_axis.dimensions_count
        col_dims = self._col_axis.dimensions_count

        # title
        title = str(self)
        text += ("-" * 80) + "\n"
        text += f"{title}\n"
        text += ("-" * 80) + "\n"

        # header dimensions
        for member in self._filter_axis.positions[0]:
            text += f"{member.dimension.name} := {member.name}\n"

        # col headers
        for c in range(self._col_axis.dimensions_count):  # range(col_dims):
            for r in range(self._row_axis.dimensions_count):  # range(row_dims):
                text += " ".ljust(row_header_width)
            for position in self._col_axis.positions:  # self.grid_cols_count):
                caption = position[c].name  # self.grid[i][3][c]
                if len(caption) > cell_width:
                    caption = caption[:cell_width - 3].strip() + "..."
                text += caption.center(cell_width)
            text += "\n"

        # row headers & cells
        previous = {}
        for r in range(self._row_axis.positions_count):
            for c in range(self._col_axis.positions_count):
                value = self._cells[r][c].value
                if type(value) is float:
                    if hide_zeros and value == 0.0:
                        value = f"-".rjust(cell_width)
                    else:
                        value = f"{value:,.0f}".rjust(cell_width)
                elif value is None:
                    value = f"-".rjust(cell_width)
                else:
                    value = f"{str(value)}".rjust(cell_width)

                if c == 0:
                    if r > 0:
                        text += "\n"
                    for pos, member in enumerate(self._row_axis.positions[r]):
                        caption = member.name
                        caption = (" " * (member.dimension.get_top_level() - member.level)) + caption
                        if len(caption) > row_header_width:
                            caption = caption[:row_header_width - 3].strip() + "..."
                        if pos in previous:
                            if previous[pos] != member:
                                text += caption.ljust(row_header_width)
                            else:
                                text += " ".ljust(row_header_width)
                        else:
                            text += caption.ljust(row_header_width)
                        previous[pos] = member

                text += value
        return text

    def to_json(self, indent=None) -> str:
        """Converts the current state of the view into a json string. Useful for serialization.
        :param indent: Indentation for json formatting.
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_dict(self) -> dict:
        """Converts the current state of the view into a serializable Python dictionary."""
        """FOR INTERNAL USE! Converts the contents of the attribute field to a dict."""
        return {"contentType": Config.ContentTypes.VIEW,
                "version": Config.VERSION,
                "uid": self.uid,
                "title": self.title,
                "description": self.description,
                "database": str(self.cube.database.name),
                "cube": str(self.cube.name),
                "statistics": self._statistics.to_dict(),
                "axes": {
                    "filters": self._filter_axis.to_dict(),
                    "rows": self._row_axis.to_dict(),
                    "columns": self._col_axis.to_dict(),
                },
                "cells": [
                    {"row": row_id, "cells": [
                        {"row": row_id, "col": col_id, "value": cell.value,
                         "text": cell.formatted_value} for col_id, cell in enumerate(row)
                    ]} for row_id, row in enumerate(self._cells)
                ]
                }
