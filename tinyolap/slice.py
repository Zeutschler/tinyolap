import enum
import weakref
from cube import Cube

class Slice:
    """Represents a slice from a cube. Slices can be seen as a report in Excel with filters on top,
     row- and column-headers and the requested data itself. See demo.py for sample usage."""

    class Color_Scheme():

        class Colors(enum.Enum):
            none = ''
            reset = '\033[0m'
            bold = '\033[1m'
            disable = '\033[02m'
            underline = '\033[04m'
            reverse = '\033[07m'
            strikethrough = '\033[09m'
            invisible = '\033[08m'

            black = '\033[30m'
            red = '\033[31m'
            green = '\033[32m'
            orange = '\033[33m'
            blue = '\033[34m'
            purple = '\033[35m'
            cyan = '\033[36m'
            white = '\033[37m'  # aka lightgrey
            darkgrey = '\033[90m'
            lightred = '\033[91m'
            lightgreen = '\033[92m'
            yellow = '\033[93m'
            lightblue = '\033[94m'
            pink = '\033[95m'
            lightcyan = '\033[96m'

            bg_black = '\033[40m'
            bg_red = '\033[41m'
            bg_green = '\033[42m'
            bg_orange = '\033[43m'
            bg_blue = '\033[44m'
            bg_purple = '\033[45m'
            bg_cyan = '\033[46m'
            bg_white = '\033[47m'  # aka lightgrey

        def __init__(self):
            self.colors = self.Colors
            self.borders = ""
            self.negatives = ""
            self.positives = ""
            self.names = ""
            self.members = ""

    class ColorScheme_None(Color_Scheme):
        def __init__(self):
            super().__init__()

    class Color_Scheme_Default(Color_Scheme):
        def __init__(self):
            super().__init__()
            self.borders = self.colors.darkgrey
            self.negatives = self.colors.red
            self.positives = self.Colors.none
            self.names = str(self.colors.white) + str(self.colors.bg_red)
            self.members = str(self.colors.blue) + str(self.colors.bold)

    def __init__(self, cube: Cube, definition, suppress_zero_columns=False, suppress_zero_rows=False):
        # self.header_def = {}
        # self.col_def = {}
        # self.rows_def = {}
        self.axis = []
        self.grid = []
        self.grid_rows_count = 0
        self.grid_cols_count = 0
        self.zero_rows = []
        self.zero_cols = []
        self.dimensions = {}
        self.measures = []
        self.cube = cube  #weakref.ref(cube) if cube else None
        self.definition = definition
        self.suppress_zero_columns = suppress_zero_columns
        self.suppress_zero_rows = suppress_zero_rows

        self.__validate()
        self.__prepare()
        self.refresh()

    def _experimental_refresh_grid(self, parallel_execution=True):
        from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
        from time import time

        results = list()
        addresses = [tuple(arg[5]) + (arg[6],) for arg in self.grid]
        start = time()
        if parallel_execution:
            # duration, results = report._experimental_refresh_grid(False)
            # duration, results = report._experimental_refresh_grid(False)
            # print(f"Non-parallel execution (for arg in grid  loop) of slice refresh in {duration:.4} sec.")
            # duration, results = report._experimental_refresh_grid(True)
            # print(f"Parallel execution (using ProcessPoolExecutor) of slice refresh in {duration:.4} sec.")

            # finding: NOT suitable for stateful processing. ERROR on weakref serialization via pickle
            #          This tries to replicate the entire database in multiple other process rooms. HORROR!
            # with ProcessPoolExecutor() as executor:

            # finding: NOT faster then non-parallel execution
            with ThreadPoolExecutor() as executor:
                for result in executor.map(self._experimental_refresh_grid_cell, addresses):
                    # put results into correct output list:
                    results.append(result)
        else:
            for address in addresses:
                results.append(self._experimental_refresh_grid_cell(address))
        return time() - start,  results

    def _experimental_refresh_grid_cell(self, address):
        # arg := [col, row, value, col_members, row_members, address, measure]
        value = self.cube.get(address)
        return value


    def refresh(self):
        """Refreshes the data defined by the slice. Only required when data has changed since the creation
        of the Slice or since the last to 'refresh()'."""
        dim_count = len(self.cube._dimensions)
        address = [""] * dim_count
        measure = ""
        grid = []

        # set fixed header values
        for member in self.axis[0]:
            dim_ordinal = member[0]
            if dim_ordinal == -1:
                measure = member[1]
            else:
                address[dim_ordinal] = member[1]

        # iterate over columns and rows
        row = 0
        col_members = []
        row_members = []
        for row_member_set in self.axis[2]:
            row_members = []
            for row_member in row_member_set:
                dim_ordinal = row_member[0]
                row_members.append(row_member[1])
                if dim_ordinal == -1:
                    measure = row_member[1]
                else:
                    address[dim_ordinal] = row_member[1]

            col = 0
            for col_member_set in self.axis[1]:
                col_members = []
                for col_member in col_member_set:
                    dim_ordinal = col_member[0]
                    col_members.append(col_member[1])
                    if dim_ordinal == -1:
                        measure = col_member[1]
                    else:
                        address[dim_ordinal] = col_member[1]

                # now we have a valid address to be evaluated
                value = self.cube.get(tuple(address) + (measure,))
                grid.append([col, row, value, col_members, row_members, tuple(address), measure])

                col += 1
            row += 1

        self.grid = grid
        self.grid_cols_count = len(self.axis[1])
        self.grid_rows_count = len(self.axis[2])

        # execute zero suppression
        self.__zero_surpression()

    def __validate(self):
        """Validates the definition and adds missing information"""

        self.dimensions = {dim.name: False for dim in self.cube._dimensions}

        # 1. add title and description is missing
        if "title" not in self.definition:
            self.definition["title"] = None
        if "description" not in self.definition:
            self.definition["description"] = None

        self.__validate_axis("header")
        self.__validate_axis("columns", True)
        self.__validate_axis("rows", True)

        # add missing dimensions, if required
        if not all([v for v in self.dimensions.values()]):
            if "header" not in self.definition:
                self.definition["header"] = []

            # not all dimensions are defined yet, lets find suitable members
            #  for the missing dimensions and add them to the header.
            for key in self.dimensions:
                if not self.dimensions[key]:  # = if this dimension is not yet defined.
                    dimension = self.cube.get_dimension(key)
                    # use the first top level member, whatever that is and add  it wrapped in a list
                    member_list = [dimension.get_members_by_level(dimension.get_top_level())[0]]
                    self.definition["header"].append({
                        "dimension": key,
                        "member": member_list
                    })

        # add missing measure, if required
        if not self.measures:
            # simply use the first measure and wrap it into a list.
            self.measures = [list(self.cube.get_measures())[0]]
            if "header" not in self.definition:
                self.definition["header"] = []
            self.definition["header"].append({
                "measure": self.measures
            })

        return True

    def __validate_axis(self, axis: str, mandatory: bool = False):
        # 2. process header
        if axis in self.definition:
            if not type(self.definition[axis]) is list:
                raise ValueError(f"Slice axis '{axis}' expected to be of type 'list', "
                                 f"but type is {type(self.definition[axis])}.")
            for position, member_def in enumerate(self.definition[axis]):
                if not type(member_def) is dict:
                    raise ValueError(f"Slice axis '{axis}' expected to contain a list of definitions of type 'dict', "
                                     f"but instead 'dict' type {type(member_def)} was found.")
                if ("dimension" not in member_def) and ("measure" not in member_def):
                    raise ValueError(f"Slice axis '{axis}' expected to contain either keys 'dimension' or 'measure', "
                                     f"but definition '{member_def}' does contain neither.")

                # ******************************************
                # validate dimension definition
                # ******************************************
                if "dimension" in member_def:
                    if "measure" in member_def:
                        raise ValueError(
                            f"Slice axis '{axis}' contains both keys 'dimension' and 'measure' in "
                            f"definition '{member_def}', but only one key is allowed per definition.")
                    dimension = member_def["dimension"]
                    if dimension not in self.dimensions:
                        raise ValueError(
                            f"Slice axis '{axis}' contains a dimension named '{dimension}' in definition "
                            f"'{member_def}' which is not a dimension of cube '{self.cube.name}'.")
                    self.dimensions[dimension] = True

                    # check for member definition
                    if "member" not in member_def:
                        self.definition[axis][position]["member"] = \
                            self.cube.get_dimension(dimension).get_members()  # get all members as list
                    elif (not member_def["member"]) or (member_def["member"] == "*"):
                        self.definition[axis][position]["member"] = \
                            self.cube.get_dimension(dimension).get_members()  # get all members as list
                    elif type(member_def["member"]) is str:
                        # A single member has been defined
                        if not self.cube.get_dimension(dimension).member_exists(member_def["member"]):
                            raise ValueError(
                                f"Slice axis '{axis}' contains unknown member '{member_def['member']}' in "
                                f"definition '{member_def}'"
                                f"'{self.cube.name}'.")
                        self.definition[axis][position]["member"] = [member_def["member"]]  # convert to list
                    elif type(member_def["member"]) is list:
                        # just validate the list
                        for member in member_def["member"]:
                            if not self.cube.get_dimension(dimension).member_exists(member):
                                raise ValueError(f"Slice axis '{axis}' contains unknown member '{member}' in "
                                                 f"definition '{member_def}'.")
                    else:
                        raise ValueError(f"Slice axis '{axis}' contains an invalid definition '{member_def}'.")

                # ******************************************
                # validate measure definition
                # ******************************************
                elif "measure" in member_def:
                    if "dimension" in member_def:
                        raise ValueError(
                            f"Slice axis '{axis}' contains both keys 'dimension' and 'measure' in "
                            f"definition '{member_def}', but only one key is allowed per definition.")

                    measure = member_def["measure"]
                    if (not measure) or (measure == "*"):
                        self.definition[axis][position]["measure"] = self.cube.measures.keys()  # get all measures
                    if type(measure) is str:
                        if measure not in self.cube.measures:
                            raise ValueError(
                                f"Slice axis '{axis}' contains an unknown measure '{measure}' in "
                                f"definition '{member_def}'.")
                        self.definition[axis][position]["measure"] = [measure]
                    if type(measure) is list:
                        for m in measure:
                            if m not in self.cube._measures:
                                raise ValueError(
                                    f"Slice axis '{axis}' contains an unknown measure '{m}' in "
                                    f"definition '{member_def}'.")
                        self.measures = measure
                    else:
                        raise ValueError(f"Slice axis '{axis}' contains an invalid definition '{member_def}'.")

            return self.definition[axis]
        else:
            if mandatory:
                raise ValueError(f"Mandatory slice axis '{axis}' is missing.")

    def __prepare(self):
        """Prepares the slice for execution."""

        # collect all members and assign them to the axes
        axes = ["header", "columns", "rows"]
        self.axis = []
        for axis_index, axis_name in enumerate(axes):
            self.axis.append([])
            for definition in self.definition[axis_name]:
                members = []
                if "dimension" in definition:
                    dimension = definition["dimension"]
                    dim_ordinal = self.cube.get_dimension_ordinal(dimension)
                    for member in definition["member"]:
                        members.append((dim_ordinal, member, dimension))
                elif "measure" in definition:
                    for measure in definition["measure"]:
                        members.append((-1, measure))
                    pass
                else:
                    raise ValueError("Unexpect error in Slice preparation.")
                self.axis[axis_index].append(members)

            # expand (multiply) all definition of the axis
            if axis_index == 0:
                # only valid for header
                #print(f"{axis_name}:")
                members = [x[0] for x in self.axis[axis_index]]
                # print(members)
                self.axis[axis_index] = members
            else:
                # only valid for rows and columns
                no_of_definitions = len(self.definition[axis_name])
                members = []

                if no_of_definitions == 1:
                    # print(f"{axis_name}:")
                    for t in [[m0]
                              for m0 in self.axis[axis_index][0]]:
                        # print(t)
                        members.append(t)
                elif no_of_definitions == 2:
                    # print(f"{axis_name}:")
                    for t in [[m0, m1]
                              for m0 in self.axis[axis_index][0]
                              for m1 in self.axis[axis_index][1]]:
                        # print(t)
                        members.append(t)
                elif no_of_definitions == 3:
                    # print(f"{axis_name}:")
                    for t in [[m0, m1, m2]
                              for m0 in self.axis[axis_index][0]
                              for m1 in self.axis[axis_index][1]
                              for m2 in self.axis[axis_index][2]]:
                        # print(t)
                        members.append(t)
                elif no_of_definitions == 4:
                    # print(f"{axis_name}:")
                    for t in [[m0, m1, m2, m3]
                              for m0 in self.axis[axis_index][0]
                              for m1 in self.axis[axis_index][1]
                              for m2 in self.axis[axis_index][2]
                              for m3 in self.axis[axis_index][3]]:
                        # print(t)
                        members.append(t)
                elif no_of_definitions == 5:
                    # print(f"{axis_name}:")
                    for t in [[m0, m1, m2, m3, m4]
                              for m0 in self.axis[axis_index][0]
                              for m1 in self.axis[axis_index][1]
                              for m2 in self.axis[axis_index][2]
                              for m3 in self.axis[axis_index][3]
                              for m4 in self.axis[axis_index][4]]:
                        # print(t)
                        members.append(t)
                else:
                    raise ValueError(
                        f"Too many nested dimensions on axis '{axis_name}'. Max 5 nested dimension are allowed.")

                self.axis[axis_index] = members

    def __zero_surpression(self):
        # todo: implement this
        self.zero_cols = None
        self.zero_rows = None

    def as_console_output(self, color_sheme: Color_Scheme = Color_Scheme) -> str:
        """Renders an output suitable for printing to the console only. The output most probably contains
        control characters and color definitions and is therefore not suitable for other use cases."""
        # todo: implement this
        # title, decsription
        # print headers
        # print col headers
        # print row headers and values

        cell_width = 12
        row_header_width = 12

        row_dims = len(self.grid[0][4])
        col_dims = len(self.grid[0][3])

        text = "\n"

        # title
        if self.definition["title"]:
            text += ("-" * 80) + "\n"
            text += f"{self.definition['title']}\n"
            if self.definition["description"]:
                text += f"{self.definition['description']}\n"
            text += ("-" * 80) + "\n"

        # header dimensions
        for member in self.axis[0]:
            if member[0] == -1:
                text += f"Measure := {member[1]}\n"
            else:
                text += f"{member[2]} := {member[1]}\n"

        # col headers
        for c in range(col_dims):
            for r in range(row_dims):
                text += " ".ljust(row_header_width)
            for i in range(self.grid_cols_count):
                text += self.grid[i][3][c].center(cell_width)
            text += "\n"

        # row headers & cells
        for cell in self.grid:
            col = cell[0]
            row = cell[1]
            if type(cell[2]) is float:
                value = f"{cell[2]:.2f}".rjust(cell_width)
            elif cell[2] is None:
                value = f"-".rjust(cell_width)
            else:
                value = f"{str(cell[2])}".rjust(cell_width)

            if col == 0:
                if row > 0:
                    text += "\n"
                for member in cell[4]:
                    text += member.ljust(row_header_width)
            text += value

        return text

    def as_html(self) -> str:
        return str(self)

    def as_csv(self) -> str:
        return str(self)

    def __str__(self):
        return self.as_console_output(color_sheme=Slice.Color_Scheme_Default())

    def __repr__(self):
        return self.as_console_output(color_sheme=Slice.Color_Scheme_Default())
