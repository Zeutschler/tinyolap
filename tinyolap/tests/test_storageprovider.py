import datetime
import itertools
import time
from unittest import TestCase
import string
import random
from storage.sqlite import SqliteStorage
from storage.mock import MockStorage
from storage.storageprovider import StorageProvider


def some_json(data=None, size: int = 16):
    chars: str = string.ascii_lowercase + string.digits
    if not data:
        return '{"data": "' + ''.join(chars[i % len(chars)] for i in range(size)) + '"}'
    return '{"data": "' + str(data) + '"}'


class TestStorageProvider(TestCase):

    def test_sqlite_provider_read_write_data(self):
        """Read, write, overwrite, delete, rewrite of cube data."""
        database_name = "sqlite_provider_end_to_end"
        cube_names = ["this", "that", "other", "foreign", "self"]
        dim_names = ["years", "month", "regions", "models", "figures"]

        provider: StorageProvider = SqliteStorage(name= database_name)
        if provider.exists():
            provider.delete()
        provider.open()

        for i, dim_name in enumerate(dim_names):
            provider.add_dimension(dim_name, some_json(i))

        for i, cube_name in enumerate(cube_names):
            provider.add_cube(cube_name, some_json(i))

        # 3 members per dimension for/over all 5 dimension
        members = [1, 2, 3]

        # fill and check all 5 cubes with 3^5 = 243 values each
        for cube_name in cube_names:
            tuples = itertools.product(members, members, members, members, members)
            for tuple in tuples:
                address = str(tuple)
                provider.set_record(cube_name, address, some_json(i))
                value = provider.get_record(cube_name, address)
                self.assertEqual(some_json(i), value)
            # count cube records
            count = provider.count_cube_records(cube_name)
            self.assertEqual(243, count)

        # ...batch (re)fill and check
        data = []
        tuples = itertools.product(members, members, members, members, members)
        for tuple in tuples:
            data.append((str(tuple), some_json(i * 2)))
        for cube_name in cube_names:
            provider.set_records(cube_name, data)
        for cube_name in cube_names:
            tuples = itertools.product(members, members, members, members, members)
            for tuple in tuples:
                value = provider.get_record(cube_name, str(tuple))
                self.assertEqual(value, some_json(i * 2))

        # brut force random read, write and delete for 100 iterations
        for i in range(100):
            address = str((random.randint(1, 3), random.randint(1, 3), random.randint(1, 3),
                           random.randint(1, 3), random.randint(1, 3)))

            cube_name = random.choice(cube_names)
            number = round(random.random() * 100, 2)
            value = provider.get_record(cube_name, address)

            # set new value
            provider.set_record(cube_name, address, some_json(number))
            self.assertEqual(provider.get_record(cube_name, address), some_json(number))

            # delete value
            provider.set_record(cube_name, address)
            self.assertEqual(provider.get_record(cube_name, address), None)

            # reset initial value
            provider.set_record(cube_name, address, some_json(value))
            self.assertEqual(provider.get_record(cube_name, address), some_json(value))

        # close and clean up of database
        provider.close()
        provider.delete()
        self.assertEqual(provider.exists(), False)


    def test_sqlite_provider_cubes(self):
        """Creation, update and deletion of cubes and cube tables."""
        database_name = "sqlite_provider_cube_test"
        cube_names = ["this", "that", "other", "foreign", "self"]

        provider: StorageProvider = SqliteStorage(name= database_name)

        provider.open()
        if provider.count_cubes() > 0:
            for name in provider.get_cube_names():
                provider.remove_cube(name)
        self.assertEqual(provider.count_cubes(), 0)

        for i, dim in enumerate(cube_names):
            provider.add_cube(dim, some_json(i))
        self.assertEqual(provider.count_cubes(), len(cube_names))

        if provider.count_cubes() > 0:
            for name in provider.get_cube_names():
                provider.remove_cube(name)
        self.assertEqual(provider.count_cubes(), 0)

        # close and clean up of database
        provider.close()
        provider.delete()
        self.assertEqual(provider.exists(), False)

    def test_sqlite_provider_dimensions(self):
        """Creation and deletion of dimensions."""

        database_name = "sqlite_provider_dim_test"
        dim_names = ["years", "month", "regions", "models", "figures"]

        provider: StorageProvider = SqliteStorage(name=database_name)
        provider.open()

        # delete dimensions, if such already exits
        if provider.count_dimensions() > 0:
            dimensions = provider.get_dimension_names()
            for i, dim_tuple in enumerate(dimensions):
                provider.remove_dimension(dim_tuple)
        self.assertEqual(provider.count_dimensions(), 0)

        for i, dim in enumerate(dim_names):
            provider.add_dimension(dim, some_json(i))
        self.assertEqual(provider.count_dimensions(), len(dim_names))

        # close and clean up of database
        provider.close()
        provider.delete()
        self.assertEqual(provider.exists(), False)

