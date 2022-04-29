# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
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
# from tinyolap.cube import Cube
from tinyolap.utilities.hybrid_dict import HybridDict
from tinyolap.exceptions import TinyOlapViewError


@dataclass
class ViewCell:
    value: float = 0.0
    formatted_value: str = ""
    format: str = ""


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


class ViewAxisPositionMember:
    def __init__(self, view, axis, member: Member, indentation: int = 0):
        self._view = view
        self._axis = axis
        self.member = member
        self.indentation = indentation


class ViewAxisPosition:
    def __init__(self, view, axis, members: tuple[Member]):
        self._view = view
        self._axis = axis
        self._members = members
        self.all_zero: bool = False

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


class ViewAxisDimension:
    def __init__(self, dimension: Dimension):
        self.dimension: Dimension = dimension
        self.top_level: int = 0


class ViewAxis(Iterable[ViewAxisPosition]):

    def __init__(self, view, idx, dimensions, member_lists):
        self._view = view
        self._positions: tuple[ViewAxisPosition] = tuple()

        if isinstance(dimensions, Iterable):
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

        # member indentations (needed for row axis mainly)
        self.indentations = []

    def _add(self, idx, dimension, member):
        """Adds a dimension to the view axis."""
        self._dimensions = tuple(list(self._dimensions) + [dimension, ])
        self._dim_members = tuple(list(self._dim_members) + [MemberList(dimension, member), ])
        self._dim_idx = tuple(list(self._dim_idx) + [idx, ])
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
            {"dimension": dim.name, "ordinal": ordinal, "members":
                [member.name for member in self._dim_members[ordinal]]}
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

    def __init__(self, cube, name=None, description=None,
                 definition=None,
                 zero_suppression_on_rows: bool = False,
                 zero_suppression_on_columns: bool = False,
                 uid=None,
                 random_view: bool = False,
                 use_first_root_members_for_filters: bool = False,
                 title: str = ""):
        """
        Initializes a new view for the given cube.
        :param cube: The Cube to create a view for.
        :param name: (optional) the name of the view. If no name is defined a random name will be created.
        :param description: (optional) a description for the view.
        :param definition: (optional) a valid view definition. If no view definition is provided, then
            a default view definition, based on the cubes structure, will be created. For details on how to
            create view definitions please see the TinyOlap documentation, or create a default view and
            the a look the dict object returned by the 'definition' property.
        :param zero_suppression_on_rows: Identifies is zero suppression should be applied to the rows of the view.
        :param zero_suppression_on_columns: Identifies is zero suppression should be applied to the columns of the view.
        :param uid: A uid of the view object. Useful for client/server interaction, persistence and state management.
        :param random_view: Flag to force the creation of a random view, instead of the default view, upon
            the given cube. Only valid for the case that no view definition is defined.
        :param use_first_root_members_for_filters: Flag to force to set the first root member for all filter dimensions.
            This applies to both random views and the default view.
        :param title: (optional) Title for the report, if not defined in view definition.
        """
        self._cube = cube
        self._definition = definition
        self._row_zero: bool = zero_suppression_on_rows
        self._col_zero: bool = zero_suppression_on_columns
        self._cells = []
        if not name:
            name = str(uuid.uuid4())[:8]
        self._name = name

        self._title = title
        self._description: str = ""
        self._default_number_format: str = "{:,.0f}"
        self._uid: str = str(uid) if uid else str(uuid.uuid4())
        self._random_view: bool = random_view
        self._use_first_root_members_for_filters = use_first_root_members_for_filters
        self._statistics: ViewStatistics = ViewStatistics()

        self._last_refresh = None

        # process the view definition, or create a default definition
        if self._definition is None:
            self._create_default_definition()
        else:
            filters, rows, columns = self._parse(self._definition)
            self._filter_axis: ViewAxis = filters
            self._row_axis: ViewAxis = rows
            self._col_axis: ViewAxis = columns

    @property
    def cube(self):
        """Returns the cube of the view."""
        return self._cube

    @property
    def definition(self) -> dict:
        """Returns the cube of the view."""
        return self._definition

    @definition.setter
    def definition(self, value: dict):
        """Sets the title of the view."""
        if self._parse(value):
            self._definition = value
        raise TinyOlapViewError(f"An unknown error occurred while pasring view '{self.name}'")

    @property
    def uid(self) -> str:
        """Returns the uid of the view. Useful for client/server interaction, persistence and state management."""
        return self._uid

    @property
    def title(self) -> str:
        """Returns the title of the view."""
        return self._title

    @property
    def name(self) -> str:
        """Returns the name of the view."""
        return self._name

    @property
    def last_refresh(self) -> datetime:
        """Returns the datetime when the view was last refreshed."""
        if not self._last_refresh:
            return datetime.min
        return self._last_refresh

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
    def default_number_format(self) -> str:
        """Returns the default number format for the view in Python format.
        The default number format is: "{:,.0f}"."""
        return self._default_number_format

    @default_number_format.setter
    def default_number_format(self, value: str):
        """Sets the default number format for the view in Python format.
        Number formats defined for one of the dimension members
        used in the view will override the default format.
        Default format is: "{:,.0f}"."""
        self._default_number_format = value

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
        number_format = 0
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[0][i].index
            super_level += axis.positions[0][i].level
            if axis.positions[0][i].number_format:
                number_format = axis.positions[0][i].number_format
        axis = self._row_axis
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[row][i].index
            super_level += axis.positions[row][i].level
            if axis.positions[0][i].number_format:
                number_format = axis.positions[0][i].number_format
        axis = self._col_axis
        for i in range(axis._dim_count):
            idx_address[axis._dim_idx[i]] = axis.positions[col][i].index
            super_level += axis.positions[col][i].level
            if axis.positions[0][i].number_format:
                number_format = axis.positions[0][i].number_format

        value = self.cube._get((super_level, tuple(idx_address),))
        if number_format:
            return ViewCell(value, number_format.format(value), number_format)
        else:
            return ViewCell(value, self._default_number_format.format(value), number_format)

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
        return self._name

    def __str__(self):
        return self._name

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

    def validate(self, definition: dict) -> (bool, str):
        """Validates if a view definition is valid. Does not raises an error"""
        try:
            filters, rows, columns = self._parse(definition)
        except TinyOlapViewError as err:
            return False, str(err)
        except Exception as err:
            return False, f"Internal Fatal Error. {str(err)}"
        return True, None

    def _parse(self, definition: dict):
        """Parses a view definition. If successful the view will be prepared for execution."""

        # read all (relevant) metadata
        if "name" in definition:
            self._name = definition["name"]
        if "title" in definition:
            self._title = definition["title"]
        if "description" in definition:
            self._description = definition["description"]
        if "cube" in definition:
            if self._cube.name.lower() != str(definition["cube"]).lower():
                raise TinyOlapViewError(f"Failed to parse view definition. Attribute 'cube' = "
                                        f"'{definition['name']}' does not match the name of the "
                                        f"cube the view has been created for: '{self._cube.name}'.")

        # get all defined axis
        filter_axis = None
        row_axis = None
        column_axis = None
        if "filters" in definition:
            filter_axis = self._parse_axis(definition["filters"], "filters", False)
        else:
            filter_axis = ViewAxis(self, [], [], [])
        if "rows" in definition:
            row_axis = self._parse_axis(definition["rows"], "rows")
        else:
            row_axis = ViewAxis(self, [], [], [])
        if "columns" in definition:
            column_axis = self._parse_axis(definition["columns"], "columns")
        else:
            column_axis = ViewAxis(self, [], [], [])

        # are dimensions missing?
        missing_dims = self._get_missing_dims((filter_axis, row_axis, column_axis))
        if missing_dims:
            # add members for all missing dimensions to the filter axis
            for dim in missing_dims:
                ordinal = self._cube.get_dimension_ordinal(dim)
                filter_axis._add(idx=ordinal, dimension=dim, member=dim.default_member)

        return filter_axis, row_axis, column_axis

    def _get_missing_dims(self, axes):
        cube = self._cube
        dimensions = list(cube.dimensions)
        for axis in axes:
            if axis:
                for dim in axis.dimensions:
                    if dim in dimensions:
                        dimensions.remove(dim)
        return dimensions

    def _parse_axis(self, axis_definition, axis_name: str,
                    return_all_members_if_no_members_defined: bool = True) -> ViewAxis:
        axis = axis_definition
        dimensions = []
        member_lists = []
        dim_idx = []
        if "dimensions" in axis:
            dims = axis["dimensions"]
            if not isinstance(dims, Iterable) or type(dims) is str:
                # Not a list of dimensions!!! Then try to evaluate for a
                # simple dimension name e.g. "years", or a list of such e.g. "years, months, products"
                dim_names = str(dims)
                # we allow ',' and ';' as separators
                if "," in dim_names:
                    dim_names = [dim.strip() for dim in dim_names.split(",")]
                elif ";" in dim_names:
                    dim_names = [dim.strip() for dim in dim_names.split(";")]
                else:
                    dim_names = (dim_names,)

                # validate the dimension names
                for dim_name in dim_names:
                    ordinal = self._cube.get_dimension_ordinal(dim_name)
                    if ordinal == -1:
                        raise TinyOlapViewError(f"Failed to parse view definition. Attribute 'dimensions' = "
                                                f"'{dims}' on {axis_name}-axis definition is invalid."
                                                f"At least '{dim_name}' is not a dimension of cube '{self._cube.name}'.")

                    # add the dimension with default member or all members
                    dimension = self._cube.dimensions[dim_name]
                    dim_idx.append(ordinal)
                    dimensions.append(dimension)
                    if return_all_members_if_no_members_defined:
                        members = list(dimension.members)
                    else:
                        members = [dimension.default_member, ]
                    member_lists.append(MemberList(dimension, members))

            else:
                for ordinal, dim in enumerate(dims):
                    # get attributes from definition
                    if "dimension" not in dim:
                        # Not a list of dimension definitions!!! Then try to evaluate for a
                        # simple dimension names e.g. "years"
                        dim_name = str(dim)
                        ordinal = self._cube.get_dimension_ordinal(dim_name)
                        if ordinal == -1:
                            raise TinyOlapViewError(f"Failed to parse view definition. Attribute 'dimensions' = "
                                                    f"'{dim_name}' on {axis_name}-axis definition is invalid."
                                                    f"'{dim_name}' is not a dimension of cube '{self._cube.name}'.")

                        # add the dimension with default member or all members
                        dimension = self._cube.dimensions[dim_name]
                        dim_idx.append(ordinal)
                        if return_all_members_if_no_members_defined:
                            members = list(dimension.members)
                        else:
                            members = [dimension.default_member, ]
                    else:
                        dim_name = dim["dimension"]
                        # get dimension and members
                        if dim_name not in self._cube.dimensions:
                            raise TinyOlapViewError(f"Invalid dimension in view definition. '{dim_name}', "
                                                    f"at 'dimension' at position {ordinal} "
                                                    f"in {axis_name}-axis definition, is not a dimension of "
                                                    f"cube '{self._cube.name}'.")
                        dimension = self._cube.dimensions[dim_name]

                        if "members" in dim:
                            member_names = dim["members"]
                            if not isinstance(member_names, Iterable):
                                member_names = (member_names,)

                            # FOR FUTURE USE - use of ordinal in axis
                            if "ordinal" in dim:
                                ordinal = dim["ordinal"]
                                if not (type(ordinal) is int or float):
                                    if str(ordinal).isnumeric():
                                        ordinal = int(ordinal)
                                    else:
                                        ordinal = 0
                                else:
                                    ordinal = int(ordinal)  # float -> int, if required

                            dim_idx.append(self._cube.get_dimension_ordinal(dimension))
                            members = []
                            for pos, member_name in enumerate(member_names):
                                if not dimension.member_exists(member_name):
                                    raise TinyOlapViewError(f"Invalid member in view definition. '{member_name}' "
                                                            f"at position {pos} for the 'dimension' at position {ordinal} "
                                                            f"in {axis_name}-axis definition if not a member of dimension "
                                                            f"'{dimension.name}'.")
                                member = dimension.members[member_name]
                                members.append(member)
                        else:
                            # if no members are defined, return the default or all members.
                            if return_all_members_if_no_members_defined:
                                members = list(dimension.members)
                            else:
                                members = [dimension.default_member, ]

                    dimensions.append(dimension)
                    member_lists.append(MemberList(dimension, members))

            return ViewAxis(self, idx=tuple(dim_idx), dimensions=tuple(dimensions), member_lists=tuple(member_lists))
        else:
            # no filter in axis defined, that's ok (maybe)
            return ViewAxis(self, [], [], [])

    def refresh(self) -> View:
        """Refreshes the view from the database."""

        # todo: Refresh should also work in no row axis or no col axis is defined, and also for both.

        # prepare statistics
        stat = self._statistics
        stat.refresh_duration = time.time()
        stat.executed_cell_requests = self._cube.counter_cell_requests
        stat.executed_cell_aggregations = self._cube.counter_aggregations
        stat.executed_rules = self._cube.counter_rule_requests

        # refresh filter axis first to create a FactTableRowSet
        cells = []
        number_format = ""
        filter_level = 0
        idx_address = [0] * self._cube.dimensions_count
        axis = self._filter_axis
        for d in range(axis._dim_count):
            member = axis.positions[0][d]
            if isinstance(member, Iterable):
                member = member[0]
            idx_address[axis._dim_idx[d]] = member.index
            filter_level += member.level
            if member.number_format:
                number_format = member.number_format
        if axis._dim_count:
            row_set = self._cube._facts.create_row_set(idx_address)
        else:
            row_set = set()

        # refresh rows and columns
        rows = self._row_axis
        cols = self._col_axis
        indent = []
        indent_max = [0] * rows._dim_count
        for row in range(rows.positions_count):
            super_level = filter_level
            for d in range(rows._dim_count):
                idx_address[rows._dim_idx[d]] = rows.positions[row][d].index
                member = rows.positions[row][d]
                super_level += member.level
                # prepare indentation
                if member.level > indent_max[d]:
                    indent_max[d] = member.level
                if d == 0:
                    indent.append([member.level])
                else:
                    indent[row].append(member.level)

                if member.number_format:
                    number_format = member.number_format

            all_zero = True
            for col in range(cols.positions_count):
                for d in range(cols._dim_count):
                    member = cols.positions[col][d]
                    idx_address[cols._dim_idx[d]] = member.index
                    super_level += member.level
                    if member.number_format:
                        number_format = member.number_format

                value = self._cube._get((super_level, tuple(idx_address),), row_set=row_set)

                if type(value) is not float:
                    if value is None:
                        formatted_value = ""
                    else:
                        all_zero = False
                        formatted_value = str(value)
                else:
                    if value != 0.0:
                        all_zero = False

                    if not number_format:
                        formatted_value = self._default_number_format.format(value)
                    else:
                        formatted_value = number_format.format(value)

                view_cell = ViewCell(value, formatted_value, number_format)
                if col == 0:
                    cells.append([view_cell, ])
                else:
                    cells[row].append(view_cell)

            rows.positions[row].all_zero = all_zero

        # update indentations
        for p in range(len(indent)):
            for d in range(rows.dimensions_count):
                indent[p][d] = indent_max[d] - indent[p][d]
        rows.indentations = indent

        # save results
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

        self._last_refresh = datetime.now()

        return self

    def _create_default_definition(self):
        """Creates a default view definition for the cube.

        The last dimension of the cube will be placed in the column axis of the view,
        the previous last (if such exists) in the row axis and all remaining dimensions
        will be placed in the filter axis. If a randomized view is requested, then dimensions
        will be shuffled and for all filter dimensions a random member will be selected."""

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
            if not self._use_first_root_members_for_filters or self._random_view:
                self._filter_axis = ViewAxis(self,
                                             idx=tuple([ordinal[idx] for idx in range(remaining)]),
                                             dimensions=tuple([dimensions[ordinal[idx]] for idx in range(remaining)]),
                                             member_lists=tuple(
                                                 [MemberList(dimension=dimensions[ordinal[idx]],
                                                             members=random.choice(dimensions[ordinal[idx]].members))
                                                  for idx in range(remaining)]))
            else:
                self._filter_axis = ViewAxis(self,
                                             idx=tuple([ordinal[idx] for idx in range(remaining)]),
                                             dimensions=tuple([dimensions[ordinal[idx]] for idx in range(remaining)]),
                                             member_lists=tuple(
                                                 [MemberList(dimension=dimensions[ordinal[idx]],
                                                             members=dimensions[ordinal[idx]].members[0])
                                                  for idx in range(remaining)]))

        # create report definition
        definition = {
            "contentType": Config.ContentTypes.VIEW_DEFINITION,
            "version": Config.VERSION,
            "database": str(self.cube.database.name),
            "cube": self._cube.name,
            "name": self._name,
            "title": self.title,
            "description": self.description,
            "zeroSuppressionOnRows": self.zero_suppression_on_rows,
            "zeroSuppressionOnColumns": self.zero_suppression_on_columns,
            "filters": self._filter_axis.to_dict(),
            "rows": self._row_axis.to_dict(),
            "columns": self._col_axis.to_dict(),
        }
        self._definition = definition

    def as_console_output(self, hide_zeros: bool = True) -> str:
        """Renders the view suitable for console output. The output contains
        control characters and color definitions and is therefore not suitable
        for other use cases."""

        if not self._last_refresh:
            self.refresh()

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

        if not self._last_refresh:
            self.refresh()

        return {"contentType": Config.ContentTypes.VIEW,
                "version": Config.VERSION,
                "uid": self.uid,
                "database": str(self.cube.database.name),
                "cube": self._cube.name,
                "name": self._name,
                "title": self.title,
                "description": self.description,
                "zeroSuppressionOnRows": self.zero_suppression_on_rows,
                "zeroSuppressionOnColumns": self.zero_suppression_on_columns,
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

    def to_html(self, endless_loop: bool = False) -> str:
        """Converts the current state of the view into a simple static HTML representation."""

        if not self._last_refresh:
            self.refresh()

        start = time.time()

        tro = "<tr>"
        trc = "</tr>\n"
        table = ""

        # header dimensions
        table += '<table class="table w-auto"><tbody>\n'
        for position in self._filter_axis.positions:
            for member in position:
                table += f'<tr><td>{member.dimension.name}</td><th scope="row">{member.name}</th></tr>\n'
        table += '</tbody></table>'

        table += '<div style= width: 100%">'
        table += '<div class"table-responsive">' \
                 '<table class="table table-hover table-striped table-bordered"' \
                 '>\n'
        table += '<thead">\n'

        row_dims = self._row_axis.dimensions_count
        col_dims = self._col_axis.dimensions_count

        # column headers
        dim_names_inserted = False
        table += tro
        for c in range(col_dims):
            for r in range(row_dims):
                if dim_names_inserted:
                    table += f'<th scope="col" class="th-lg" style="width: 80px"></th>\n'
                else:
                    dim_names = ", ".join(
                        "→" + dimension.name for dimension in self._col_axis.dimensions)  # .definition["columns"])
                    dim_names = dim_names + "</br>" + ", ".join(
                        "↓" + dimension.name for dimension in self._row_axis.dimensions)  # self.definition["rows"])
                    table += f'<td scope="col" class="td-lg" style="width: 80px">{dim_names}</td>\n'
                    dim_names_inserted = True
            for d in range(self._col_axis.dimensions_count):
                for position in self._col_axis.positions:
                    table += f'<th scope="col" class="text-center" style="width: 80px">' \
                             f'{position[d].name}' \
                             f'</th>\n'

        table += trc
        table += '</thead">\n'

        # row headers and cells
        previous = {}
        table += tro
        rows = self._row_axis
        cols = self._col_axis
        zero_rows = 0
        for row in range(rows.positions_count):
            hide_this_row = self.zero_suppression_on_rows and rows.positions[row].all_zero
            if hide_this_row:
                zero_rows += 1
            else:
                for col in range(cols.positions_count):
                    cell = self._cells[row][col]

                    # row headers
                    if col == 0:
                        if row > 0:
                            table += trc
                            table += tro

                        for pos, member in enumerate(rows.positions[row]):
                            if pos in previous:
                                if previous[pos] != member.name:
                                    indentation = rows.indentations[row][pos]
                                    indent = "&nbsp;&nbsp;&nbsp;" * indentation  # member.level
                                    table += f'<th class="text-nowrap" scope="row">{indent + member.name}</th>\n'
                                else:
                                    table += f'<th class="text-nowrap" scope="row"></th>\n'
                            else:
                                indentation = rows.indentations[row][pos]
                                indent = "&nbsp;&nbsp;&nbsp;" * indentation  # member.level
                                table += f'<th class="text-nowrap" scope="row">{indent + member.name}</th>\n'
                            previous[pos] = member.name

                    value = cell.value
                    formatted_value = cell.formatted_value
                    negative = False
                    if type(value) is float:
                        negative = (value < 0.0)
                    if negative:
                        table += f'<td class="text-nowrap" style="text-align: right; color:darkred">{formatted_value}</td>\n'
                    else:
                        table += f'<td class="text-nowrap" style="text-align: right">{formatted_value}</td>\n'

        table += trc
        table += "</table></div>"

        # title
        title = ""
        if self.title:
            title = f"<h2>{self.title} on cube '{self.cube.database.name}:{self.cube.name}'</h2>\n"
            if self.description:
                table += f"<h4>{self.description}</h4>\n"

        stat = self.statistics
        statistics = f'<div class="font-italic font-weight-light">View ' \
                     f'refreshed in {stat.refresh_duration:.5} sec, ' \
                     f'{stat.executed_cell_requests:,} cells, ' \
                     f'{stat.executed_cell_aggregations:,} aggregations, ' \
                     f'{stat.executed_rules:,} rules, zero-suppression ' \
                     f'is {"ON" if self.zero_suppression_on_rows else "OFF"}' \
                     f', {zero_rows:,} rows suppressed.</div>'

        duration = time.time() - start
        duration = f'<div class="font-italic font-weight-light">HTML rendered in {duration:.5} sec, ' \
                   f'total time {duration + stat.refresh_duration:.5} sec.' \
                   f'</div>'

        loop = ""
        if endless_loop:
            loop = """<script>window.location.reload();</script>"""

        html = f'<!doctype html>' \
               f'<html lang="en">' \
               f'<head><!-- Required meta tags -->' \
               f'<meta charset="utf-8">' \
               f'<meta name="viewport" content="width=device-width, initial-scale=1">' \
               f'<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"/> ' \
               f'<title>TinyOlap API (sample random view)</title>' \
               f'<style></style>' \
               f'</head>' \
               f'<body>' \
               f'<div class="p-3">' \
               f'{title}' \
               f'{statistics}' \
               f'{table}' \
               f'</div>' \
               f'{duration}' \
               f'{loop}' \
               f'</body></html>'
        return html


class ViewList:
    """
    Represents a list of views.
    """

    def __init__(self, cube):
        self._cube = cube
        self._views = HybridDict[View]()

    def __len__(self):
        return len(self._views)

    def __iter__(self):
        for view in self._views:
            yield view

    def __getitem__(self, item):
        return self._views[item]

    def __contains__(self, item):
        return item in self._views

    @property
    def cube(self):
        return self._cube

    def create(self, name: str, random_view_layout: bool = False) -> View:
        """
        Creates a new (default) view. A view can afterwards be modified and saved.
        :param name: Name of the view to be created.
        :param random_view_layout: (optional) flag that identifies to create random layout for the view.
            Valuable for testing or demo purposes mainly.
        :return: The newly created view.
        """
        if name in self._views:
            raise KeyError(f"Failed to create view. A view named '{name}' already exists.")
        view = View(cube=self._cube, name=name, random_view=random_view_layout)
        self._views.append(view)
        return view

    def add(self, view: View) -> View:
        if view.name in self._views:
            raise KeyError(f"Failed to add view. A view named '{view.name}' already exists.")
        self._views.append(view)
        return view
