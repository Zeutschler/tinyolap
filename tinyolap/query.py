import itertools
import sqlparse

from database import Database
from cube import Cube


class Query:
    """
    Basic implementation of a SQL query interface for TinyOlap cubes.
    """

    def __init__(self, db: Database, sql: str = None,
                 include_column_names: bool = False):
        """
        Create a new query object for the given database.
        :param db: The database to query against.
        :param sql: (optional) An SL statement to be executed.
        :param include_column_names: Include column names in the resultset.
        :param include_cube_name: Include a cube name column in the resultset.
        """
        self.database = db
        self.sql = sql
        self._records = []
        self._include_column_names = include_column_names

    @property
    def include_column_names(self):
        return self._include_column_names

    @include_column_names.setter
    def include_column_names(self, value: bool):
        self._include_column_names = value

    @property
    def records(self):
        """
        The records returned by the query. Records contain the address and the current value of the queried cells.
        :return: An array of arrays, the outer array represents the rows
        """
        return self._records

    def execute(self, sql: str = None):
        """
        Executes an SQL statement against the defined database.
        :param sql: The SQL statement to execute.
        :return: True, if the execution was successful, False otherwise.
        :raises NotImplementedError: Raised if a certain SQL language capability is not supported.
        :raises KeyError: If a certain name (e.g. cube, dimension, member, subset) does not exists in the database.
        :raises SyntaxError: If a SQL statement contains a syntax error or is incomplete.
        """
        if sql:
            self.sql = sql
        self._records = []
        statement = sqlparse.split(self.sql)
        if len(statement) > 1:
            raise NotImplementedError(f"Multiple sql statements are not yet supported. "
                                      f"A single sql statement was expected, but multiple satements were "
                                      f"found in {self.sql}.")
        self.parsed = sqlparse.parse(statement[0])[0]

        tokens = self.__remove_whitespace_tokens(self.parsed.tokens)
        cube: Cube
        cube_name = None

        # resolve the cube. The token after the 'FROM' keyword should contain the cube name
        from_index = -1
        for index, token in enumerate(tokens):
            if token.is_keyword and token.normalized == "FROM":
                if index == len(tokens) - 1:  # FROM token is already the last token.
                    raise KeyError("Cube name missing after <FROM> clause.")
                from_index = index
                cube_name = tokens[index + 1].normalized
                # check for cube name
                cube = self.database.cubes.lookuptry(cube_name)
                if not cube:
                    raise KeyError(f"Cube '{cube_name}' does not exit in database '{self.database.name}'.")
                cube_name = cube.name
                break
        else:
            raise SyntaxError("<FROM> clause missing in statement.")

        # validate and prepare the query
        where_slicer = self.__resolve_where_clause(tokens)
        select_slicer = self.__resolve_select_clause(from_index, tokens)
        query_def = self.__validate_query(cube, select_slicer, where_slicer)

        # execute the query
        records = []
        if self._include_column_names:
            records.append(self.__get_column_names(query_def))
        members_tuples = [tuple(dimension["members"]) for dimension in query_def["dims"]]
        addresses = itertools.product(*members_tuples)
        if not select_slicer:
            for address in addresses:
                value = cube[address]  # get a value from the database
                record = list(address)
                record.append(value)
                records.append(record)
        else:
            fields = query_def["fields"]
            for address in addresses:
                record = []
                value_already_appended = False
                value = None
                for field in fields:
                    value = cube[address]  # get a value from the database
                    if type(field) is int:
                        if field == -1:
                            record.append(value)
                            value_already_appended = True
                        else:
                            record.append(address[field])
                    else:
                        # get an attribute for the current member of a dimension
                        member = address[field["member_index"]]
                        attribute = field["dimension"].get_attribute(field["attribute"], member)
                        record.append(attribute)

                if not value_already_appended:
                    record.append(value)

                records.append(record)


            pass

        self._records = records
        return True

    def __get_column_names(self, query_def):
        col_names = []
        value_already_appended = False
        if "fields" in query_def:
            for field in query_def["fields"]:
                if field == -1:
                    col_names.append("value")
                    value_already_appended = True
                elif type(field) is dict:
                    col_names.append(f"{field['dimension'].name}.{field['attribute']}")
                else:
                    col_names.append(query_def["dims"][field]["dimension"].name)
        else:
            for dimension in query_def["dims"]:
                col_names.append(dimension["dimension"].name)
        if not value_already_appended:
            col_names.append("value")
        return col_names

    def __resolve_where_clause(self, tokens):
        where_slicer = []
        where_tokens = [token for token in tokens if type(token) is sqlparse.sql.Where]
        if where_tokens:
            if type(where_tokens[0].tokens[-1]) is sqlparse.sql.IdentifierList:
                identifiers = where_tokens[0].tokens[-1].get_identifiers()
                where_slicer = [self.__strip(str(x)) for x in identifiers]
        return where_slicer

    def __resolve_select_clause(self, from_index, tokens):
        select_tokens = tokens[1:from_index]
        if len(select_tokens) == 1 and select_tokens[0].normalized =="*":
            return []  # special case: SELECT * FROM ...
        select_slicer = self.__resolve_identifiers(
            [token for token in select_tokens[0].tokens])
        return select_slicer

    def __validate_query(self, cube: Cube, select_slicer: list, where_slicer: list):
        dim_count = cube.dimensions_count
        db = cube._database
        query_def = {"cube": cube, "db": db, "dim_count": dim_count,
                     "dims": [{"dimension": cube.get_dimension_by_index(d),
                               "members": [],
                               "expression": None} for d in range(cube.dimensions_count)]}

        # Process the WHERE statement
        unresolved_dims = list(range(dim_count))
        for slice in where_slicer:
            dim, member = self.__dim_member_split(slice)
            if dim:  # a dimension name is defined, e.g.: years:'2022'
                for index, dimension in enumerate(query_def["dims"]):
                    if dimension["dimension"].name.lower() == dim.lower():
                        if dimension["dimension"].member_exists(member):
                            dimension["members"].append(member)
                            unresolved_dims.remove(index)
                        else:
                            # check for subset name
                            if member in dimension["dimension"].subsets:
                                dimension["members"] = dimension["dimension"].subsets[member][3]
                                unresolved_dims.remove(index)
                            if member == "*":
                                dimension["members"] = dimension["dimension"].get_members()
                                unresolved_dims.remove(index)

                            # check for member list e.g.: (Jan, 'Feb')
                            elif member.startswith('(') and member.endswith(')'):
                                members = self.__strip_brackets(member)
                                members = members.split(",")
                                members = [self.__strip(member) for member in members]
                                invalid_members = []
                                for member in members:
                                    if not dimension["dimension"].member_exists(member):
                                        invalid_members.append(member)
                                if invalid_members:
                                    raise KeyError(f"Invalid member list for dimension {dimension['dimension'].name} "
                                                   f" in WHERE statement found. The following members do not exist: "
                                                   f"{', '.join(invalid_members)}")
                                dimension["members"] = members
                                unresolved_dims.remove(index)

            else:  # only a member name is defined, e.g.: '2022' > resolve the dimension
                found_index = -1
                for d in unresolved_dims:
                    if query_def["dims"][d]["dimension"].member_exists(member):
                        query_def["dims"][d]["members"].append(member)
                        found_index = d
                        break
                if found_index > -1:
                    unresolved_dims.remove(found_index)
                else:
                    # If it's not a member then it might be a list of members or the name of a subset.

                    raise KeyError(f"Unresolvable member '{slice}' in WHERE statement found.")

        # for all unresolved dimensions, get the (default) first member of the dimension.
        for d in unresolved_dims:
            member = query_def["dims"][d]["dimension"].get_first_member()
            query_def["dims"][d]["members"].append(member)

        # If there is no specific SELECT statement, we're already done
        #   esp. for 'SELECT * FROM ...' statements
        query_def["is_cell_request"] = True
        if not select_slicer:
            return query_def

        # Process the SELECT statement
        fields = []
        for slicer in select_slicer:
            found = False

            # search for 'value' keyword
            if slicer.lower() == "value":
                fields.append(-1)
                found = True

            # search for dimension names, if found remember their index
            if not found:
                for d in range(dim_count):
                    if query_def["dims"][d]["dimension"].name.lower() == slicer.lower():
                        found = True
                        fields.append(d)
                        break

            # search for attribute names
            if not found:
                dim, attribute = self.__dim_attribute_split(slicer)
                found = attribute is not None
                if found:
                    found = False
                    for d in range(dim_count):
                        if query_def["dims"][d]["dimension"].name.lower() == dim.lower():
                            if query_def["dims"][d]["dimension"].has_attribute(attribute):
                                fields.append({"dimension":query_def["dims"][d]["dimension"],
                                               "attribute": attribute,
                                               "member_index": d})
                                found = True
                                break
                    # if not found:
                    #     raise KeyError(f"Unresolvable attribute name '{slice}' "
                    #                    f"after SELECT statement found.")

            # not supported or unable to resolve
            if not found:
                raise KeyError(f"Unresolvable field or keyword '{slice}' "
                               f"after SELECT statement found.")

        query_def["fields"] = fields
        return query_def

    def __dim_member_split(self, expression: str):
        dim = None
        member = None
        if "=" in expression:
            tokens = expression.split("=", maxsplit=1)
            dim = self.__strip(tokens[0])
            member = self.__strip(tokens[1])
        elif ":" in expression:
            tokens = expression.split(":", maxsplit=1)
            dim = self.__strip(tokens[0])
            member = self.__strip(tokens[1])
        else:
            member = expression
        return dim, member

    def __dim_attribute_split(self, expression: str):
        dim = None
        attribute = None
        if "." in expression:
            tokens = expression.split(".", maxsplit=1)
            dim = self.__strip(tokens[0])
            attribute = self.__strip(tokens[1])
        elif ":" in expression:
            tokens = expression.split(":", maxsplit=1)
            dim = tokens[0]
            attribute = self.__strip(tokens[1])
        else:
            dim = expression
        return dim, attribute

    @staticmethod
    def __strip(text: str):
        """
        Removes surrounding double or single quotes from a text. Even if nested.
        :param text: The text to be stripped.
        :return: The stripped version of the text.
        """
        text = text.strip()
        while True:
            if text.startswith("'") and text.endswith("'") and len(text) > 1:
                text = text[1:-1].strip()
            elif text.startswith('"') and text.endswith('"') and len(text) > 1:
                text = text[1:-1].strip()
            else:
                return text

    @staticmethod
    def __strip_brackets(text: str):
        """
        Removes surrounding brackets [], {} or (). Even if nested.
        :param text: The text to be stripped.
        :return: The stripped version of the text.
        """
        text = text.strip()
        while True:
            if text.startswith("(") and text.endswith(")") and len(text) > 1:
                text = text[1:-1].strip()
            elif text.startswith("[") and text.endswith("]") and len(text) > 1:
                text = text[1:-1].strip()
            elif text.startswith("{") and text.endswith("}") and len(text) > 1:
                text = text[1:-1].strip()
            else:
                return text

    @staticmethod
    def __remove_whitespace_tokens(tokens):
        return [token for token in tokens if not token.is_whitespace]

    def __resolve_identifiers(self, tokens):
        return [self.__strip(str(token.normalized)) for token in tokens if type(token) is sqlparse.sql.Identifier]

    def __str__(self):
        return self.sql

    def __repr__(self):
        return self.sql
