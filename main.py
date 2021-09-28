import time


def string_comparisons():

    l = ["super glue", "Super Glue"," SuPer GluE   ", " SUPER GlUE  ", "SUPER GlUE ","sUPER GlUe"]
    t = tuple(l)
    loops = 1_000_000

    # empty loop
    start = time.time()
    z = 0
    while z < loops:
        z = z + 1
    duration_empty_loop = time.time() - start

    # naive loop list
    start = time.time()
    z = 0
    ll = []
    while z < loops:
        for text in l:
            ll.append(text.strip().lower())
        z = z + 1
    duration = time.time() - start - duration_empty_loop
    print(f"Naive local approach: {loops:,} loops records in {duration:.3}sec")

    # optimized loop list
    start = time.time()
    z = 0
    while z < loops:
        strip = str.strip
        lower = str.lower
        ll = []
        append = ll.append
        for text in l:
            append(strip(lower(text)))
        z = z + 1
    duration = time.time() - start - duration_empty_loop
    print(f"Optimized loop: {loops:,} loops records in {duration:.3}sec")

    # list comprehension loop list
    start = time.time()
    z = 0
    strip = str.strip
    lower = str.lower
    while z < loops:
        ll = [strip(lower(text)) for text in l]
        z = z + 1
    duration = time.time() - start - duration_empty_loop
    print(f"List comprehension: {loops:,} loops records in {duration:.3}sec")

    # list comprehension strip only
    start = time.time()
    z = 0
    strip = str.strip
    lower = str.lower
    while z < loops:
        ll = [strip(text) for text in l]
        z = z + 1
    duration = time.time() - start - duration_empty_loop
    print(f"List comprehension strip only: {loops:,} loops records in {duration:.3}sec")

    # list comprehension lower only
    start = time.time()
    z = 0
    strip = str.strip
    lower = str.lower
    while z < loops:
        tt = (lower(text) for text in t)
        z = z + 1
    duration = time.time() - start - duration_empty_loop
    print(f"List comprehension strip only: {loops:,} loops records in {duration:.3}sec")


def main():
    string_comparisons()


if __name__ == "__main__":
    main()
