import math
import sys

import numpy as np

class BitArray:
    def __init__(self, initial_size: int = 1024):
        self._size: int = initial_size
        self._word_size: int = int(math.log2(sys.maxsize * 2 + 2))  # this should return 64
        self._words_count: int = (max(0, (initial_size - 1)) // self._word_size + 1)
        self._max_size = self._words_count * self._word_size
        self._words = np.zeros(self._words_count, dtype=np.uint)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value: int):
        self._size = value
        self._words_count: int = (max(0, (value - 1)) // 64 + 1)
        self._words.resize((self._words_count,))

    def set_bit(self, index: int):
        """
        Sets the bit at a specific position to true.
        :param index: The position (or index) of the bit to set.
        """
        word: int = index // self._word_size
        bit: int = index - word * self._word_size

        print(f"words[{word}] := {format(self._words[word],'b')}")
        self._words[word] = self._words[word] | (1 << bit)
        print(f"words[{word}] := {format(self._words[word],'b')}")

    def clear_bit(self, index: int):
        word: int = index // self._word_size
        bit: int = index - word * self._word_size

        print(f"words[{word}] := {format(self._words[word],'b')}")
        self._words[word] = self._words[word] & ~(1 << bit)
        print(f"words[{word}] := {format(self._words[word],'b')}")

    def clone(self):
        """
        Creates a shallow copy of the BitArray.
        """
        new_bitarray = BitArray(self._size)
        new_bitarray._words = np.copy(self._words)
        return new_bitarray

    def __and__(self, other):  # and (equal to) operator
        new_bitarray = BitArray(self._size)
        new_bitarray._words = self._words & other._words
        return new_bitarray

    def __iand__(self, other):  # and (equal to) operator
        self._words = self._words & other._words
        return self

    def __or__(self, other):  # or (equal to) operator
        new_bitarray = BitArray(self._size)
        new_bitarray._words = self._words | other._words
        return new_bitarray

    def __ior__(self, other):  # or (equal to) operator
        self._words = self._words | other._words
        return self

    def __repr__(self):
        return f"{format(self._words[0], 'b')}..."

    def __str__(self):
        return f"{format(self._words[0], 'b')}..."

    def get_bits(self) -> list[int] :
        bits = []
        for i in range(self._words_count):
            if self._words[i]:
                for b in range(self._word_size):
                    mask = 1 << b
                    if self._words[i] & mask:
                        bits.append( i * self._word_size + b)
        return bits

a = BitArray()
a.set_bit(0)

b = BitArray()
b.set_bit(4)

c = a | b
print(c)
print(c.get_bits())