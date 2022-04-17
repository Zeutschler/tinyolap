# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import time
import os

from art import *

import tinyolap.cell
from decorators import rule
from tinyolap.database import Database
from tinyolap.rules import RuleScope
from tinyolap.slice import Slice
from samples.planespotter_model.flight_data import FlightData, Location

location = Location(52.5200, 13.4050)  # Berlin (Germany)
radius = 250  # around the location
raster_size = 50  # 50 >>> creates a 10 x 10 raster from -250 km to 250 km
flight_data = FlightData(location, radius)  # returns real-time flight data from https://opensky-network.org


def create_database(console_output: bool = False):
    """Creates a dynamic database with airplane data from the defined location and radius."""

    if console_output:
        print(f"Creating the 'plane-spotter' data model. Please wait...")

    # 1. create a new database
    db = Database("planespotter", in_memory=True)

    # 2. create required dimensions
    # Create 2 dimensions to make a 2-D raster of 10 km blocks to count planes
    dim_horz = db.add_dimension("horz").edit()
    dim_vert = db.add_dimension("vert").edit()
    for i in range(-radius - raster_size, +radius + raster_size, raster_size):
        dim_horz.add_member("Total", f"{i:+} km")
        dim_vert.add_member("Total", f"{i:+} km")
    dim_horz.commit()
    dim_vert.commit()

    # Create a dimension for plane names (the actual plane names will be added later)
    dim_plane = db.add_dimension("planes").edit()
    dim_plane.add_member("some plane")
    dim_plane.add_member("All", "some plane")
    dim_plane.commit()

    # Create a dimension for plane data
    dim_data = db.add_dimension("data").edit()
    dim_data.add_member(["count", "altitude"])
    dim_data.commit()
    dim_data.member_set_format("altitude", "{:,.0f} ft")

    # 3. Add a plane data cube
    cube = db.add_cube("planes", [dim_horz, dim_vert, dim_plane, dim_data])
    cube.register_rule(rule_average_altitude)

    # That's it! Database is ready to get loaded
    return db


@rule("planes", ["altitude"], scope=tinyolap.rules.RuleScope.AGGREGATION_LEVEL)
def rule_average_altitude(c: tinyolap.cell.Cell):
    """
    Rule to calculate the average altitude for all aggregated cells.
    """
    altitude = c["altitude", c.BYPASS_RULES]
    count = c["count"]
    if count != 0.0:
        return altitude / count
    return None


def update_database_from_flight_data(db: Database):
    """Updates the flight data and the database based on the new data."""
    dim_planes = db.dimensions["planes"]
    cube = db.cubes["planes"]

    start = time.time()
    data = flight_data.update()
    duration_flight_data = time.time() - start

    start = time.time()

    # update planes dimension. Also build a hierarchy by plane's countries.
    dim_planes.edit()
    new_planes = list(plane[0] for plane in data)
    countries = list(plane[1] for plane in data)
    planes_to_remove = set(dim_planes.get_leaves()).difference(set(new_planes))
    if planes_to_remove:
        dim_planes.remove_member(list(planes_to_remove))
    for idx, plane in enumerate(new_planes):
        if plane:  # Note: some planes have no name (e.g. military air-planes)
            dim_planes.add_member("All", countries[idx])
            dim_planes.add_member(countries[idx], plane)
            # dim_planes.add_member(plane)
            # dim_planes.add_member("All", plane)
    dim_planes.commit()

    # clear all data from the cube and import the new data
    cube.clear()
    for plane in data:
        name, country, distance, vert_distance, horz_distance, altitude = plane

        if name:
            horz_distance = round(horz_distance / raster_size, 0) * raster_size
            if horz_distance > radius:
                horz_distance = radius
            elif horz_distance < -radius:
                horz_distance = -radius
            horz = f"{int(horz_distance):+} km"

            vert_distance = round(vert_distance / raster_size, 0) * raster_size
            if vert_distance > radius:
                vert_distance = radius
            elif vert_distance < -radius:
                vert_distance = -radius
            vert = f"{int(vert_distance):+} km"

            address = (horz, vert, name, "count")
            cube.set(address, 1)
            address = (horz, vert, name, "altitude")
            if not altitude:
                altitude = 0.0
            cube.set(address, float(altitude))

    duration_tinyolap = time.time() - start
    return cube, duration_flight_data, duration_tinyolap


def play_plane_spotter(console_output: bool = True):

    if console_output:
        tprint("TinyOlap", font="Slant")

    database = create_database(console_output)

    if console_output:
        print(f"\tRetrieving real-time flight data from 'OpenSky'. Please wait...")

    cube, duration_flight_data, duration_tinyolap = update_database_from_flight_data(database)

    if console_output:
        os.system('cls' if os.name == 'nt' else 'clear')

    dim_planes = database.dimensions["planes"]
    plane_list = ["All", ] + sorted(dim_planes.get_members_by_level(1)) + sorted(dim_planes.get_leaves())

    report_definition = {"title": f"Planes {radius:,} km around Berlin...",
                         "header": [{"dimension": "planes", "member": "All"},
                                    {"dimension": "data", "member": "count"}],
                         "columns": [{"dimension": "vert"}],
                         "rows": [{"dimension": "horz"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    report_definition = {"title": f"First 10 planes (out of {len(dim_planes)})...",
                         "header": [{"dimension": "vert", "member": "Total"},
                                    {"dimension": "horz", "member": "Total"}],
                         "rows": [{"dimension": "data"}],
                         "columns": [{"dimension": "planes", "member": plane_list}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    if console_output:
        print(f"\tRetrieving data from 'OpenSky Flight Data' in {duration_flight_data:.3} sec.")
        print(f"\tRebuild TinyOlap data model and import flight data in {duration_tinyolap:.3} sec.")


def main():
    play_plane_spotter()


if __name__ == "__main__":
    main()
