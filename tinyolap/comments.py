import random
from datetime import datetime
from faker import Faker

class CellCommentPost:
    """Represents a single comment post from a single user."""
    def __init__(self, comment: str, user: str, timestamp: datetime):
        self._comment = comment
        self._user = user
        self._timestamp = timestamp

    def __str__(self):
        return f"{self._comment} ({self._user} {self._timestamp.strftime('%m/%d/%Y, %H:%M:%S')})"

    def __repr__(self):
        return f"{self._comment} ({self._user} {self._timestamp.strftime('%m/%d/%Y, %H:%M:%S')})"

    @property
    def comment(self) -> str:
        return self._comment

    @comment.setter
    def comment(self, value: str):
        self._comment = value
        self._timestamp = datetime.now()

    @property
    def user(self) -> str:
        return self._user

    @property
    def timestamp(self) -> datetime:
        return self._timestamp



class CellComments:
    """Represents the comment thread for a single cell in a cube.
    The thread can contain multiple posts for various users."""
    def __init__(self, comment:CellCommentPost):
        self._comments: list[CellCommentPost] = list()
        if comment:
            self._comments.append(comment)

    def __getitem__(self, index) -> CellCommentPost:
        return self._comments[index]

    def __setitem__(self, index, value: CellCommentPost):
        self._comments[index] = value

    def __len__(self):
        return len(self._comments)

    def __delitem__(self, index):
        del (self._comments[index])

    def __iter__(self):
        for comment in self._comments:
            yield comment

    def clear(self):
        self._comments.clear()

    def append(self, comment: CellCommentPost):
        self._comments.append(comment)

    def __str__(self):
        return ", ".join([str(comment) for comment in self._comments])

    def __repr__(self):
        return ", ".join([str(comment) for comment in self._comments])


class CubeComments:
    """Provides access to the cell comments of the cube.
    Cell comments can be applied to all levels in cube, also aggregated cells.
    Cell comments are stored in a flat table made up by the cell addresses.
    So, they are not represented in multidimensional space."""
    def __init__(self, cube):
        self._cube = cube
        self._cell_comments = dict()
        Faker.seed(0)
        self._fake = Faker()

    def __getitem__(self, idx_address) -> CellComments:
        if random.random() < 0.05:
            # todo remove this random comment generation.
            comment = self._fake.paragraph(nb_sentences=random.randrange(1,5))
            user = self._fake.user_name()
            return CellComments(CellCommentPost(comment=comment, user=user, timestamp=datetime.now()))
        return self._cell_comments.get(idx_address, None)

    def __setitem__(self, idx_address, value: CellComments):
        self._cell_comments[idx_address] = value

    def __len__(self):
        return len(self._cell_comments)

    def __delitem__(self, idx_address):
        del(self._cell_comments[idx_address])

    def __iter__(self):
        for comment in self._cell_comments.values():
            yield comment

    def clear(self):
        self._cell_comments.clear()

    def contains(self, idx_address):
        return idx_address in self._cell_comments

