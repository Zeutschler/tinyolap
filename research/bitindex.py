import itertools
import sys
import math

dims = 4

print(sys.maxsize)
print(math.log2(sys.maxsize * 2 + 2))

for size in [8, 15]:   #, 32, 31]:
    addresses = itertools.product(list(range(1, size)), repeat=dims)

    index = set()

    doublets = 0
    count=0
    max = 0
    for address in addresses:
        count += 1
        binary = "".join(format(key, "0"+ str(len(format(size,"b"))) + "b") for key in address)
        integer = int(binary, 2)
        if integer > max:
            max = integer
        # print(f"{address} => {binary}")
        if integer in index:
            # raise IndexError("Duplicate key")
            doublets += 1
        index.add(integer)

    print(f"size = {size}, total = {count}, "
          f"doublets = {doublets}, in % = {doublets/count:.3%}, "
          f"max = {max},")



import numpy as np
import timeit
import time
from bitvector import BitVector

def get_np(a, b):
    # idx = np.nonzero(np.bitwise_and(a, b))
    idx = np.bitwise_and(a, b)
    return idx


size = 1000000
for count in [1, 10, 100, 500, 1000, 5000, 10000, 50000, 100000]:
    s1 = set(int(x) for x in range(count))
    s2 = set(int(x*2 + 1) for x in range(count))
    s3 = set()

    ds = time.time()
    loops = 1000
    for i in range(loops):
        s3 = s1.intersection(s2)
    ds = (time.time() - ds) / loops
    print(f"set({size}, {count}) := {ds:.08f}")
    print(f"len := {len(s3)}")







