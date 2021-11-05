from abc import ABC, abstractmethod


class AbstractRepository(ABC):

    @abstractmethod
    def open(self, path: str, name:str):
        """
        Opens the repository for read/write access.
        :param path: Path or location identifier where the repository is located.
        :param name: Name of the repository, without a specific extension.
        :return: ``True`` if successful,``False`` otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """
        Closes the repository.
        :return: ``True`` if successful,``False`` otherwise.
        """
        raise NotImplementedError



class SqliteRepository(AbstractRepository):

    def __init__(self):
        pass

    def open(self, path: str, name:str):