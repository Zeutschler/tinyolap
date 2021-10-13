from __future__ import annotations
import base64
import requests
import math
from math import sin, cos, asin, sqrt, atan2, radians, degrees


class BoundingBox:
    """Represents a bounding box for locations."""

    def __init__(self, location: Location, radius_km: float):
        """Creates a quadratic BoundingBox with a side length of 2 x 'radius_km' kilometers,
        centered over a given location."""
        self.location = location
        self.km = radius_km
        self.top_left = location.shift(-radius_km, -radius_km)
        self.bottom_right = location.shift(radius_km, radius_km)

    @classmethod
    def from_locations(cls, top_left: Location, bottom_right: Location):
        """Creates a rectangular BoundingBox from two top-left and bottom-right locations."""
        return BoundingBox(top_left.center(bottom_right), top_left.distance_to(bottom_right))


class Location:
    """Wraps a location made of latitude and Longitude."""

    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

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

    def displace(self, theta: float, distance: float):
        """Displace a location by theta degrees counterclockwise and some km in that direction.
        for details see: http://www.movable-type.co.uk/scripts/latlong.html
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
        self.df_col_names = ['icao24', 'callsign', 'origin_country', 'time_position', 'last_contact', 'long', 'lat',
                             'baro_altitude', 'on_ground', 'velocity', 'true_track', 'vertical_rate', 'sensors',
                             'geo_altitude', 'squawk', 'spi', 'position_source']
        self.lookup = dict((key, idx) for idx, key in enumerate(self.df_col_names))

    def update(self) -> list[tuple]:
        data = []
        try:
            response = requests.get(
                f"{base64.b16decode('68747470733A2F2F416E6E653A6F70656E736B79406F70656E736B792D6E6574776F726B2E6F72672F6170692F7374617465732F616C6C'.encode('ascii')).decode('ascii')}" \
                f"?lamin={self.bounding_box.top_left.latitude}&lomin={self.bounding_box.top_left.longitude}" \
                f"&lamax={self.bounding_box.bottom_right.latitude}&lomax={self.bounding_box.bottom_right.longitude}").json()
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
                vert_distance = -s * Location(self.center_location.latitude, plane[long], ).distance_to(
                    self.center_location)
                s = sign(self.center_location.latitude - plane[lat])
                horz_distance = -s * Location(plane[lat], self.center_location.longitude).distance_to(
                    self.center_location)
                data.append((plane[self.lookup["callsign"]], plane[self.lookup["origin_country"]],
                             distance, vert_distance, horz_distance,
                             plane[self.lookup["baro_altitude"]]))
        finally:
            return data
