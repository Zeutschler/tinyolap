# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import datetime
import multiprocessing as mp
import random
import time

from art import *

from tinyolap.cell_context import CellContext
from tinyolap.cube import Cube
from tinyolap.database import Database
from tinyolap.decorators import rule
from tinyolap.dimension import Dimension
from tinyolap.rules import RuleScope
from tinyolap.slice import Slice


def load_tiny42(console_output: bool = False) -> Database:
    """Create a small (empty) template database for sensor data of our marmalade machines."""
    if console_output:
        print(f"Creating the 'tiny42' template database. Please wait...")
    db = Database("tiny42_template", in_memory=True)
    dim_time = db.add_dimension("time").edit().add_member(
        "Total").commit()  # , f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}").commit()
    dim_sensors = db.add_dimension("sensors").edit().add_member("machine", "sensor").commit()
    dim_values = db.add_dimension("values").edit().add_member(["count", "temperature"]).commit()
    db.add_cube("sensors", [dim_sensors, dim_time, dim_values])
    return db


def machine(arg):
    """This is our simulated and asynchronously called 'remote machine'
    for producing marmalade. Each emits some senor data for 10 seconds.
    And each machine has a different set of sensors with individual IDs."""

    machine_db, machine_id, console_output = arg[0]

    # rename the database to machine name
    start = time.time()
    machine_name = f"m_{machine_id:04d}"
    machine_db.rename(machine_name)
    if console_output:
        print(f"\t Machine {machine_name} started.")

    # get database objects
    dim_sensors = machine_db.dimensions["sensors"]
    dim_time: Dimension = machine_db.dimensions["time"]
    cube: Cube = machine_db.cubes["sensors"]

    # add machine with some sensors (2 to 10) to the 'sensor' dimension
    sensors = [f"{machine_name}_s_{i:02d}" for i in range(random.randrange(2, 10))]
    dim_sensors.edit().add_member(machine_name, sensors).commit()

    # create some sensor data for simulated 10 seconds - we won't wait, but just create the timestamps
    # set a random start temperature for the machine (37° indicate, they're humanoid machines, somehow)
    temperature = random.normalvariate(37.0, 2.0)
    # ... and also set a random start time (0 to 5 seconds offset) for more realism
    machine_start_time = datetime.datetime.now() + datetime.timedelta(seconds=float(random.randrange(0, 5)))
    for s in range(10):
        # create timestamp and add it to the 'time' dimension
        ts = machine_start_time + datetime.timedelta(seconds=float(s))
        timestamp = f"{ts:%Y-%m-%d %H:%M:%S}"
        if not dim_time.member_exists(timestamp):
            dim_time.edit().add_member(timestamp).commit()

        # write 'count' and 'temperature' value for all sensors to the 'sensors' cube
        for sensor in sensors:
            address_count = tuple([sensor, timestamp, "count"])
            cube.set(address_count, 1.0)  # counter is always = 1.0

            address_temperature = tuple([sensor, timestamp, "temperature"])
            temperature = temperature + random.normalvariate(0.0, 0.1)  # temperature is slightly moving
            cube.set(address_temperature, temperature)

    # where done already...
    if console_output:
        print(f"\t Machine {machine_name} finished in {time.time() - start:.4} sec.")
    return machine_db


def consolidate(template: Database, machine_dbs: list[Database]) -> Database:
    # create a copy of the template and consolidate all machine databases
    consolidated_db = template.clone()
    consolidated_db.rename("TinyMarmaladeFactory")

    # get all time stamps from all machine_dbs and adjust the time dimension
    timestamps = set()
    for machine_db in machine_dbs:
        timestamps.update(machine_db.dimensions["time"].get_members())
    timestamps = list(timestamps)
    timestamps.sort()
    timestamps.remove("Total")
    consolidated_db.dimensions["time"].edit().add_member("Total", timestamps).commit()

    # get all sensors from all machine_dbs and adjust the sensor dimension
    dim_sensors = consolidated_db.dimensions["sensors"].edit()
    for machine_db in machine_dbs:
        machine_name = machine_db.dimensions["sensors"].get_root_members()[1]
        dim_sensors.add_member("Total", machine_name)
        sensor_names = machine_db.dimensions["sensors"].member_get_children(machine_name)
        dim_sensors.add_member(machine_name, sensor_names)
    # lets also remove the unneeded template members
    dim_sensors.remove_member(["sensor", "machine"])
    dim_sensors.commit()

    # import the data fram all machines
    target = consolidated_db.cubes["sensors"]
    for value in consolidated_db.dimensions["values"].get_members():  # this will return ["count", "temperature"]
        for machine_db in machine_dbs:
            source = machine_db.cubes["sensors"]
            for record in source.area(str(value)).records():
                target.set(record[:3], record[3])

    # add some business logic
    target.add_rule(rule_average_temperature)

    # where done already...
    return consolidated_db


@rule("sensors", ["temperature"], scope=RuleScope.AGGREGATION_LEVEL, volatile=False)
def rule_average_temperature(c: CellContext):
    """Calculate the average temperature for all aggregated values."""
    count = c["count"]
    temperature = c["temperature", c.BYPASS_RULES]
    if count != 0.0:
        return temperature / count
    return "n.a."


def play_tiny42(console_output: bool = True):
    """

    :param console_output:
    :return:
    """
    if console_output:
        tprint("TinyOlap", font="Slant")

    # 1. create a template database
    template_db = load_tiny42()
    number_of_machines = 42

    # 2. create 42 clones the template database - it's a clone army ;-)
    if console_output:
        print(f"Creating {number_of_machines}x machine clones. Please wait...")
    start = time.time()
    machine_dbs = [(template_db.clone(), i + 1, console_output) for i in range(number_of_machines)]

    # 3. Parallel processing (multiprocessor based) of the 42 database cloles
    if console_output:
        print(f"Generating machine data for {number_of_machines}x machine in parallel. Please wait...")
    # https://stackoverflow.com/questions/43002766/apply-a-method-to-a-list-of-objects-in-parallel-using-multi-processing
    NUM_CORES = 8  # adjust to the number of cores you want to use
    pool = mp.Pool(NUM_CORES)
    processed_dbs = pool.map(machine, ((db, id + 1, console_output) for id, db in enumerate(machine_dbs)))
    pool.close()
    pool.join()

    # 4. collect all data into one database.
    consolidated_db = consolidate(template_db, processed_dbs)
    duration = time.time() - start

    # 5. print sensor data from 2 random machine_dbs and the consolidated database
    for db in [processed_dbs[random.randrange(number_of_machines)],
               processed_dbs[random.randrange(number_of_machines)],
               consolidated_db]:
        cube = db.cubes["sensors"]
        report_definition = {"title": f"Sensor data from '{db.name}'", "columns": [{"dimension": "time"}],
                             "rows": [{"dimension": "sensors"}, {"dimension": "values"}, ]}
        report = Slice(cube, report_definition)
        if console_output:
            print(report)

    if console_output:
        print(f"{number_of_machines}x machines generated, called, processed"
              f" and consolidated in in {duration:.4} sec.")


def main():
    play_tiny42(console_output=True)


if __name__ == "__main__":
    main()
