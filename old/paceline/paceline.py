# Copyright (c) 2021, Thomas Zeutschler
# All rights reserved.

# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import sys
import time
import functools
from typing import List


def paceline(function=None, *, iterations: int = 1, skip: bool = False, progressbar: bool = True,
             statistics: bool = False, boxplot: bool = False, histogram: bool = False,
             return_metrics: bool = False, suppress_output: bool = False):
    """
    A decorator for simple performance measurement of function execution time. 
    Requires your code to be contained in or wrapper by a function.

    Attributes
    ----------
    function : func
        The function to be benchmarked.
    iterations : int
        The number of iterations to be executed. Default value is 1.
        For values greater than 1, additional statistics on execution times will be calculated.
    skip : bool
        If set to True, the paceline measurement will be skipped, hence not executed. Default value is False.
    progressbar : bool
        Shows a progressbar while. Default value is True.
    statistics : bool
        Prints basic statistics over the execution time. Default value is False.
    boxplot : bool
        Prints a boxplot for execution times. Default value is False.
    histogram : bool
        Prints a histogram of execution times if set to True. Default value is False.
        Note: Only available if echo is set to True and iterations are set to a value greater than 1.
    return_metrics : bool
        If set to True, all results will be printed to the console. If set to False, results will not be shown,
        but a tuple containing the function result and a dictionary containing the paceline results will be shown.
        Default value is True.
    """
    def update_progressbar(current, total, bar_length=90, message: str = "paceline: "):
        bar_length = bar_length - len(message)
        if bar_length < 20:
            bar_length = 20
        percent = float(current) / float(total)
        bar = '#' * int(percent * bar_length)
        space = '_' * (bar_length - len(bar))
        sys.stdout.write(f"\r{message}[{bar}{space}] {percent:.2%}")
        sys.stdout.flush()

    def decorator_paceline(function) -> object:
        BOLD = "\033[1m"
        RED = "\033[31m"  # if you don't like Red, change it...
        GRAY = "\033[37m"
        RESET = "\033[0m"

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            # Sorry for the spaghetti code, some refactoring would help.
            if skip | (iterations < 1):
                return function(*args, **kwargs)


            r = None
            durations: List[float] = []
            duration_cum: float = 0.0
            last_progress_update: float = 0.0
            progress_message = f"⏱Measuring {BOLD}{function.__name__}(){RESET} "
            if (not suppress_output) & progressbar:
                update_progressbar(0, iterations, message=progress_message)

            # main loop for performance measurement iterations
            for n in range(0, iterations):
                start = time.perf_counter()
                r = function(*args, **kwargs)
                stop = time.perf_counter()

                duration = stop - start
                duration_cum += duration
                durations.append(duration)
                if (not suppress_output) & progressbar & (duration_cum > last_progress_update + 0.1):
                    update_progressbar(n, iterations, message=progress_message)
                    last_progress_update = duration_cum

            if (not suppress_output) & progressbar:
                update_progressbar(100, 100, message=progress_message)
                time.sleep(0.01)  # just to ensure users can perceive the 100% bar once
                sys.stdout.write("\r")
                sys.stdout.flush()

            min_, max_, sum_, mean = 0.0, 0.0, 0.0, 0.0
            median, q1, q3, iqr = 0.0, 0.0, 0.0, 0.0
            if iterations == 1:
                median = durations[0]
                sum_ = median
            else:
                durations = sorted(durations)
                # basic statistics
                min_ = min(durations)
                max_ = max(durations)
                sum_ = sum(durations)
                mean = sum_/len(durations)

                # median & quartiles
                n = len(durations)
                m = int(n // 2)
                median = (sum(durations[n//2-1:n//2+1])/2.0, durations[n//2])[n % 2] if n else None
                q1 = (sum(durations[:m][m//2-1:m//2+1])/2.0, durations[:m][m//2])[m % 2] if m else None
                q3 = (sum(durations[-m:][m//2-1:m//2+1])/2.0, durations[-m:][m//2])[m % 2] if m else None
                iqr = q3 - q1
            # evaluate unit of measurement, sec vs. msec
            unit = "s"
            unit_sum = "s"
            factor = 1.0
            factor_sum = 1.0
            if mean < 0.5:
                factor = 1000.0
                unit = "ms"
            if sum_ < 0.5:
                factor_sum = 1000.0
                unit_sum = "ms"
            span = "n.a."
            if mean > 0.0:
                span = f"{min_/mean:.0%} - {max_/mean:.0%}"

            if not suppress_output:
                if iterations == 1:
                    print(f"⏳paceline for {BOLD}{function.__name__}(){RESET} runtime is "
                          f"{BOLD}{mean * factor:,.3f}{unit}{RESET},"
                          f" 1x iteration in {BOLD}{mean * factor:,.3f}{unit}{RESET}")
                else:
                    print(f"⏳paceline for {BOLD}{function.__name__}(){RESET} runtime is "
                          f"{BOLD}{mean * factor:.3f}{unit}"
                          f"{RESET} on avg, {BOLD}{median * factor:.3f}{unit}{RESET} at median, "
                          f"{iterations:,}x iterations in {BOLD}{sum_ * factor_sum:,.3f}{unit_sum}{RESET}")

                    if statistics:
                        print(f"           min = {BOLD}{min_ * factor:.3f}{unit}{RESET}, "
                              f"max = {BOLD}{max_ * factor:.3f}{unit}{RESET}, "
                              f"iqr = {BOLD}{iqr * factor:.3f}{unit}{RESET}, "
                              f"span over avg = {BOLD}{span}{RESET}")

                    if boxplot:
                        print(f"           boxplot {RED}|{RESET}min={BOLD}{min_ * factor:.3f}{unit}{RESET} {RED}--->"
                              f"|{RESET} q1={BOLD}{q1 * factor:.3f}{unit}{RESET} {RED}--->{RESET} "
                              f"median={BOLD}{median * factor:.3f}{unit}{RESET} {RED}<--- {RESET}"
                              f"q3={BOLD}{q3 * factor:.3f}{unit}{RESET} {RED}|<---{RESET}"
                              f" max={BOLD}{max_ * factor:.3f}{unit}{RESET}{RED}|{RESET}")

                    if histogram:
                        bins = 71
                        max_height = 7
                        bar_char = f"{RED}{BOLD}#{RESET}"
                        line_char = f"{GRAY}_{RESET}"
                        no_bar_char = line_char
                        span = max_ - min_
                        hits = [0] * (bins + 1)
                        for duration in durations:
                            hit: int = int(round((duration - min_) / span * bins))
                            hits[hit] += 1
                        max_bin_hits = max(hits)
                        norm_bin_hits = \
                            [max([1 if b > 0 else 0, int(round(max_height * b / max_bin_hits))]) for b in hits]
                        # draw histogram
                        h: int
                        for h in range(max_height, 0, -1):
                            row: str = "           |"
                            for b in range(0, bins + 1):
                                if norm_bin_hits[b] >= h:
                                    row += bar_char
                                else:
                                    row += no_bar_char
                            if h == max_height:
                                caption = f"{max_bin_hits} hits"
                            elif h == 1:
                                caption = f"0 hits"
                            else:
                                caption = ""
                            print(row + f"| {caption}")

            if return_metrics:
                if iterations == 1:
                    metrics = {"function": function.__name__, "iterations": 1, "uom": "s", "paceline": duration}
                else:
                    metrics = {"function": function.__name__, "iterations": iterations, "uom": "s",
                               "paceline": mean, "min": min_, "max": max_, "total-time": sum_,
                               "mean": mean, "median": median, "q1": q1, "q3": q3, "iqr": iqr,
                               "span": span}
                return r, metrics
            else:
                return r

        return wrapper

    if function is None:
        return decorator_paceline
    else:
        return decorator_paceline(function)
