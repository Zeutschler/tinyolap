import itertools
import sqlparse

from database import Database
from cube import Cube


class Query:
    """
    Basic implementation of a SQL query interface for TinyOlap cubes.
    """
    def __init__(self, db: Database, sql:str = None):
        self.database = db
        self.sql = sql
        self._records = []

    @property
    def tokens(self):
        return self.parsed.tokens

    @property
    def records(self):
        return self._records

    def execute(self, sql:str = None):
        """
        Executes an SQL statement against the defined database.
        :param sql: (optional) The SQL statement to execute.
        :return: True if the execution was successful, False otherwise.
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

        tokens = self.__remove_whitespace_tokens( self.parsed.tokens)
        cube: Cube

        # resolve cube. The token after the 'FROM' keyword should contain the cube name
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
                break
        else:
            raise SyntaxError("<FROM> clause missing in statement.")

        # resolve WHERE clause, if defined. The WHERE clause is a group token
        where_slicer = []
        where_tokens = [token for token in tokens if type(token) is sqlparse.sql.Where]
        if where_tokens:
            if type(where_tokens[0].tokens[-1]) is sqlparse.sql.IdentifierList:
                identifiers = query.tokens[-1].tokens[-1].get_identifiers()
                where_slicer = [self.__strip(str(x)) for x in identifiers]

        # resolve SELECT clause. Get all tokens between SELECT and FROM
        select_tokens = tokens[1:from_index]
        select_slicer = [self.__strip(str(token.normalized)) for token in select_tokens]
        if select_slicer:
            # special case: SELECT * FROM ...
            if len(select_slicer) == 1 and select_slicer[0] == "*":
                select_slicer = []

        # validate and prepare the query
        query_def = self.__validate_query(cube, select_slicer, where_slicer)

        # execute the query
        records = []
        members_tuples = [tuple(dimension["members"]) for dimension in query_def["dims"]]
        addresses = itertools.product(*members_tuples)
        if query_def["is_cell_request"]:
            for address in addresses:
                value = cube[address]
                record = list(address)
                record.append(value)
                records.append(record)
        else:
            pass

        self._records = records
        return True

    def __validate_query(self, cube: Cube, select_slicer: list, where_slicer: list):
        dim_count = cube.dimensions_count
        db = cube._database
        query_def = {"cube": cube, "db": db, "dim_count": dim_count,
                "dims": [{"dimension": cube.get_dimension_by_index(d),
                          "members": [],
                          "expression": None} for d in range(cube.dimensions_count)],
                     "is_cell_request": False}

        # process the WHERE statement
        unresolved_dims = list(range(dim_count))
        for slice in where_slicer:
            dim, member = self.__dim_member_split(slice)
            if dim: # a dimension name is defined, e.g.: years:'2022'
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

            else: # only a member name is defined, e.g.: '2022' > resolve the dimension
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
            if query_def["dims"][d]["dimension"].get_first_member():
                query_def["dims"][d]["members"].append(member)

        # If there is no specific SELECT statement, we're already done
        #   esp. for 'SELECT * FROM ...' statements
        if not select_slicer:
            return query_def




    def __dim_member_split(self, expression: str):
        dim = None
        member = None
        if "=" in expression:
            tokens = expression.split("=", maxsplit=1)
            dim= tokens[0]
            member= self.__strip(tokens[1])
        elif ":" in expression:
            tokens = expression.split(":", maxsplit=1)
            dim= tokens[0]
            member= self.__strip(tokens[1])
        else:
            member = expression
        return dim, member


    def __strip(self, text:str):
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

    def __strip_brackets(self, text:str):
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



    def __remove_whitespace_tokens(self, tokens):
        return [token for token in tokens if not token.is_whitespace]

    def __str__(self):
        return self.sql
    def __repr__(self):
        return self.sql


