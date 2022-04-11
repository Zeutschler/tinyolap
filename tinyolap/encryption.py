# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import base64
from abc import ABC, abstractmethod

import secrets
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
from enum import Enum, IntEnum

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionMethodEnum(IntEnum):
    NoEnryption = 0
    Obfuscation = 1
    Encryption = 2


class Encryptor(ABC):
    @abstractmethod
    def encrypt(self, data: str) -> str:
        """
        Encrypts a string.
        :param data: The string data to be encrypted.
        :return: The encrypted data.
        """
        pass

    @abstractmethod
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts an encrypted string.
        :param encrypted_data: The string data to be decrypted.
        :return: The decrypted (original) data.
        """
        pass


class NotAnEncryptor(Encryptor):
    """
    WARNING: THIS IS NOT A SECURE ENCRYPTION METHOD!
    Encryption using no encryption, meaning input = output for both methods, ``encrypt()`` and ``decrypt()``.
    """

    def encrypt(self, data) -> str:
        """
        Encrypts a string.
        :param data: The string data to be encrypted.
        :return: The encrypted data.
        """
        return data

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts an encrypted string.
        :param encrypted_data: The string data to be decrypted.
        :return: The decrypted (original) data.
        """
        return encrypted_data


class ObfuscationEncryptor(Encryptor):
    """
    WARNING: THIS IS NOT A SECURE ENCRYPTION METHOD!
    Encryption by data obfuscation using base64-encoding and some shifting based on a password.
    Sufficient for minimal data protection.

    Please be aware that professional hackers will likely be able to crack this encryption quite fast.
    That said, please be also aware that if you change the default key and forget it, then you might
    need to hire and pay a professional hacker to decrypt your data.
    """

    def __init__(self, password: str = "poor man's encryption"):
        self.obfuscation_key = base64.urlsafe_b64encode(password.encode()).decode()

    def encrypt(self, data: str) -> str:
        """
        Encrypts a string.
        :param data: The string data to be encrypted.
        :return: The encrypted data.
        """
        enc = []
        for i in range(len(data)):
            key_c = self.obfuscation_key[i % len(self.obfuscation_key)]
            enc_c = chr((ord(data[i]) + ord(key_c)) % 256)
            enc.append(enc_c)
        return base64.urlsafe_b64encode("".join(enc).encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts an encrypted string.
        :param encrypted_data: The string data to be decrypted.
        :return: The decrypted (original) data.
        """
        dec = []
        enc = base64.urlsafe_b64decode(encrypted_data).decode()
        for i in range(len(enc)):
            key_c = self.obfuscation_key[i % len(self.obfuscation_key)]
            dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
            dec.append(dec_c)
        return "".join(dec)


class FernetEncryptor(Encryptor):
    """
    Encryption using Fernet encryption. (see https://cryptography.io/en/latest/fernet/).
    Can be treated as a quite secure encryption (as of 2021).
    """

    def __init__(self, password: str = "superman's encryption"):
        self.backend = default_backend()
        self.iterations = 10_000
        self.password = password

    def encrypt(self, data: str) -> str:
        """
        Encrypts a string.
        :param data: The string data to be encrypted.
        :return: The encrypted data.
        """
        return self._fernet_encrypt(data.encode(), self.password).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts an encrypted string.
        :param encrypted_data: The string data to be decrypted.
        :return: The decrypted (original) data.
        """
        return self._fernet_decrypt(encrypted_data.encode(), self.password).decode()

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """Derive a secret key from a given password and salt"""
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                         iterations=self.iterations, backend=self.backend)
        return b64e(kdf.derive(password))

    def _fernet_encrypt(self, message: bytes, password: str) -> bytes:
        salt = secrets.token_bytes(16)
        key = self._derive_key(password.encode(), salt)
        return b64e(b'%b%b%b' % (
                salt,
                self.iterations.to_bytes(4, 'big'),
                b64d(Fernet(key).encrypt(message)),
            ))

    def _fernet_decrypt(self, tokens: bytes, password: str) -> bytes:
        decoded = b64d(tokens)
        salt, iterator, token = decoded[:16], decoded[16:20], b64e(decoded[20:])
        iterations = int.from_bytes(iterator, 'big')
        key = self._derive_key(password.encode(), salt)
        return Fernet(key).decrypt(token)
