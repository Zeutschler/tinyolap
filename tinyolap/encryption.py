from abc import ABC, abstractmethod


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
        Decrypts a string.
        :param encrypted_data: The string data to be decrypted.
        :return: The decrypted (original) data.
        """
        pass


class NoEncryptor(Encryptor):
    """
    Encryption using no encryption,meaning input = output for both methods ``encrypt()`` and ``decrypt()``.
    """

    def encrypt(self, data) -> str:
        """
        Encrypts a string.
        :param data: The string data to be encrypted.
        :return: The encrypted data.
        """
        return data

    def decrypt(self, encrypted: str):
        """
        Decrypts a string.
        :param encrypted_data: The string data to be decrypted.
        :return: The decrypted (original) data.
        """
        return encrypted


