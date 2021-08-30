import pprint
from paceline import paceline


# 1. Let's define some functions that we want to paceline (= measure their performance over 1...N iterations).
@paceline(iterations=100, progressbar=True, statistics=True, boxplot=True, histogram=True, return_metrics=False)
def some_function(loops: int = 1000):
    """Some function with a paceline decorator."""
    total = 0
    for x in range(0, loops):
        for y in range(0, loops):
            total += x + y
    return total


def some_other_function(loops: int = 1000):
    """Some other function WITHOUT a paceline decorator."""
    total = 0
    for x in range(0, loops):
        for y in range(0, loops):
            total += x + y
    return total


# 2. If a function has defined the paceline decorator, like some_function(...)
#    then all calls to that function will get measured and evaluated.
some_function()
some_function()

# 3. If no decorator is defined, you to wrap your function into the paceline
#    as shown below. From thereon all calls to the function will get measured...
some_other_function = paceline(some_other_function)
print(f"\nresult = {some_other_function()}")

# 4. ...until you (optionally) unwrap the function from the decorator again, like this:
some_other_function = some_other_function.__wrapped__
print(f"\nresult (paceline decorator removed again) = {some_other_function()}")

# 5. If you just interested in the performance figures ONLY - so no output to the
#    console - you need to set <return_metrics=True> and <suppress_output=True>.
#    The <return_metrics> parameter forces the paceline decorator to return a tuple
#    of the function result(s) and the performance metrics contained in a simple
#    dictionary, suitable for any kind of further processing.
some_other_function = paceline(function=some_other_function, iterations=100, return_metrics=True, suppress_output=True)
print("\nPlease wait, paceline measurement with console output is executed...")
result, metrics = some_other_function()  # here we get the results and the metrics
print(f"result = {result}")
pprint.pprint(metrics)

print("\nThanks for testing or using...")
