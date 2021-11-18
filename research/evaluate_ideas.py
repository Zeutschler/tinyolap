import time


def dict_vs_array():

    items = 1_000_000
    d_data = []
    a_data = []
    for i in range(items):
        d_data.append({0: 1.0})
        a_data.append([1.0])

    start = time.time()
    value = 0.0
    for i in range(items):
        value = d_data[i][0]
    duration = time.time() - start
    print(f"from array of dicts {items/duration:,} ops/sec")

    start = time.time()
    value = 0.0
    for i in range(items):
        value = a_data[i][0]
    duration = time.time() - start
    print(f"from array of array {items/duration:,} ops/sec")


dict_vs_array()
