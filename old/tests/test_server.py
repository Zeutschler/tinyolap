from unittest import TestCase

from tinyolap.server import Server


class TestServer(TestCase):
    def test_open_database(self):
        self.fail()

    def test_create_database(self):
        server = Server()
        self.assertFalse(server.create_database(name="t@¢[6^^f"))  # invalid database name
        self.assertTrue(server.create_database(name="test"))  # valid database name
