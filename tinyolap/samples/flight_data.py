from __future__ import annotations
__author__ = "Thomas Zeutschler"

import json

import requests
import math
from math import sin, cos, acos, asin, sqrt, atan2, radians, degrees

class BoundingBox:
    """Represents a bounding box for locations."""

    def __init__(self, location: Location, radius_km: float):
        """
        Creates a quadratic BoundingBox with a side length of 2 x 'radius_km' kilometers,
        centered over a given location.
        """
        self.location = location
        self.km = radius_km
        self.top_left = location.shift(-radius_km, -radius_km)
        self.bottom_right = location.shift(radius_km, radius_km)

    @classmethod
    def from_locations(cls, top_left: Location, bottom_right: Location):
        """Creates a rectangular BoundingBox from two top-left and bottom-right locations."""
        return BoundingBox(top_left.center(bottom_right), top_left.distance_to(bottom_right))

    def clone(self) -> BoundingBox:
        """Create of shallow copy of the BoundingBox instance."""
        return BoundingBox(Location(self.location.latitude, self.location.longitude), self.km)

    def contains(self, location: Location) -> bool:
        """Checks if a location is contained in the current BoundingBox."""
        top = self.top_left.latitude
        left = self.top_left.longitude
        bottom = self.bottom_right.latitude
        right = self.bottom_right.longitude
        lat = location.latitude
        lon = location.longitude

        if top >= lat >= bottom:
            if left <= right and left <= lon <= right:
                return True
            elif left > right and (left <= lon or lon <= right):
                return True
        return False

    def circle_contains(self, location: Location) -> bool:
        """Checks if a location is located within the inner circle of the current BoundingBox."""
        return self.location.distance_to(location) <= self.km


class Location:
    """Wraps a location made of latitude and Longitude."""
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return f"Position([lat: {self.latitude}, lon:{self.longitude}])"

    def __str__(self):
        return f"[lat: {self.latitude}, lon:{self.longitude}]"

    def clone(self) -> Location:
        """Create of shallow copy of the Location instance."""
        return Location(self.latitude, self.longitude)

    def __sub__(self, other) -> float:
        """Returns the distance between 2 locations in km."""
        raise NotImplementedError

    def distance_to(self, other: Location) -> float:
        """Return the distance of 2 locations in km."""
        earth_radius = 6373.0
        lat1 = radians(self.latitude)
        lon1 = radians(self.longitude)
        lat2 = radians(other.latitude)
        lon2 = radians(other.longitude)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return earth_radius * 2 * atan2(sqrt(a), sqrt(1 - a))

    def shift(self, km_lat: float, km_lon: float) -> Location:
        """ Returns a location shifted by certain kilometers along the longitude and latitude."""
        return self.displace(0, km_lat).displace(90, km_lon)

    def center(self, other: Location) -> Location:
        """Evaluates the location in the center (middle) of the current and another location."""
        lat = radians(self.latitude)
        lon = radians(self.longitude)
        x = cos(lat) * cos(lon)
        y = cos(lat) * sin(lon)
        z = sin(lat)

        lat = radians(other.latitude)
        lon = radians(other.longitude)
        x += cos(lat) * cos(lon)
        y += cos(lat) * sin(lon)
        z += sin(lat)

        x = x / 2
        y = y / 2
        z = z / 2

        central_lon = atan2(y, x)
        central_square_root = sqrt(x * x + y * y)
        central_lat = atan2(z, central_square_root)

        return Location(degrees(central_lat), degrees(central_lon))

    def displace(self, theta: float, distance: float):
        """Displace a location by theta degrees counterclockwise and some km in that direction.
        Notes:
            http://www.movable-type.co.uk/scripts/latlong.html
            0 DEGREES IS THE VERTICAL Y AXIS! IMPORTANT!
        Args:
            theta:    A number in degrees.
            distance: A number in meters.
        Returns:
            A new LatLng.
        """
        earth_radius = 6373.0
        pi = math.pi
        delta = distance / earth_radius
        theta = radians(theta)
        lat1 = radians(self.latitude)
        lng1 = radians(self.longitude)
        lat2 = asin(sin(lat1) * cos(delta) + cos(lat1) * sin(delta) * cos(theta))
        lng2 = lng1 + atan2(sin(theta) * sin(delta) * cos(lat1), cos(delta) - sin(lat1) * sin(lat2))
        lng2 = (lng2 + 3 * pi) % (2 * pi) - pi
        return Location(degrees(lat2), degrees(lng2))


class FlightData:
    """
    Request and process flight data from OpenSky API
    Please refer https://opensky-network.org for further details.
    """

    def __init__(self, location: Location = None, radius: float = 0):
        self.__user_name = 'Anne'
        self.__password = 'opensky'
        self.__opensky_base_url = f"https://{self.__user_name}:{self.__password}@opensky-network.org/api/states/all"

        # set defaults, use 'Berlin' as default location
        self.__default_location = Location(52.5200, 13.4050)
        self.__default_radius_in_km = 250.0
        self.__default_bounding_box = BoundingBox(self.__default_location, self.__default_radius_in_km)

        # set initial parameters
        if location:
            self.center_location = location
        else:
            self.center_location = self.__default_location.clone()
        if radius <= 0:
            self.radius_in_km = self.__default_radius_in_km
        else:
            self.radius_in_km = radius

        self.bounding_box = BoundingBox(self.center_location, self.radius_in_km)
        self.url = self.__get_url()
        self.df_col_names = ['icao24', 'callsign', 'origin_country', 'time_position', 'last_contact', 'long', 'lat',
                             'baro_altitude', 'on_ground', 'velocity', 'true_track', 'vertical_rate', 'sensors',
                             'geo_altitude', 'squawk', 'spi', 'position_source']
        self.lookup = dict((key, idx) for idx, key in enumerate(self.df_col_names))

    def set_location(self, location: Location, radius_in_km: float = 0.0):
        """Set a new center location and a radius around that location to prepare a flight data request."""
        if radius_in_km <= 0.0:
            radius_in_km = self.radius_in_km
        if radius_in_km <= 0.0:
            radius_in_km = self.__default_radius_in_km

        self.radius_in_km = radius_in_km
        self.center_location = location.clone()
        self.bounding_box = BoundingBox(self.center_location, self.radius_in_km)

    def __get_url(self):
        lat_min = self.bounding_box.top_left.latitude
        lon_min = self.bounding_box.top_left.longitude
        lat_max = self.bounding_box.bottom_right.latitude
        lon_max = self.bounding_box.bottom_right.longitude
        return f"{self.__opensky_base_url}?lamin={lat_min}&lomin={lon_min}&lamax={lat_max}&lomax={lon_max}"

    def update(self, circular_filtering: bool = True) -> list[tuple]:
        """
        Refreshes (updates) the flight data based on the current Location and BoundingBox.
        Args:
            circular_filtering:   Flight data is always requested for a rectangular
            range. By setting apply_circular_filtering to True, then returned records
            will be filtered to be contained in the inner circle of the BoundingBox.
        Returns:
            True, if the request and refresh was executed successful, False otherwise.
        """
        data = []
        try:
            self.url = self.__get_url()
            response = requests.get(self.url).json()
            self.data_points = response['states']

            # evaluate all distances to center
            sign = lambda x: math.copysign(1, x)
            for plane in self.data_points:
                lat = self.lookup["lat"]
                long = self.lookup["long"]
                plane_location = Location(plane[lat], plane[long])

                # calculate distance between plan and center location
                distance = plane_location.distance_to(self.center_location)
                s = sign(self.center_location.longitude - plane[long])
                vert_distance = -s * Location(self.center_location.latitude, plane[long], ).distance_to(self.center_location)
                s = sign(self.center_location.latitude - plane[lat])
                horz_distance = -s * Location(plane[lat], self.center_location.longitude).distance_to(self.center_location)

                data.append((plane[self.lookup["callsign"]], plane[self.lookup["origin_country"]],
                             distance, vert_distance, horz_distance,
                             plane[self.lookup["baro_altitude"]]))
        finally:
            return data
