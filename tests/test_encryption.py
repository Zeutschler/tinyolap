from unittest import TestCase
from tinyolap.encryption import *

class TestEncryptor(TestCase):

    def test_encryptors(self):

        encryptors: list[Encryptor] = [NotAnEncryptor(),
                                       ObfuscationEncryptor(),
                                       ObfuscationEncryptor("some special password"),
                                       FernetEncryptor(),
                                       FernetEncryptor("some special password")]

        data = "The quick brown fox jumps over the lazy dog."
        for encryptor in encryptors:
            encrypted_data = encryptor.encrypt(data)
            decrypted_data = encryptor.decrypt(encrypted_data)
            self.assertEqual(data, decrypted_data)
