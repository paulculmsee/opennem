import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")


def load_facility_stations(fixture_name):
    fixture_path = os.path.join(DATA_PATH, fixture_name)

    if not os.path.isfile(fixture_path):
        raise Exception("Not a file: {}".format(fixture_path))

    fixture = None

    with open(fixture_path) as fh:
        fixture = json.load(fh)

    return fixture


FACILITY_STATIONS = load_facility_stations("facility_stations.json")


def facility_station_join_by_name(station_name):
    """
        This is a bit of a hack where we join facilities to stations by name only
        where there is no duid or other data we can join on.

        Used a lot in updating AEMO data.

        The list of station names to do this based on is stored in data/facility_stations.json

    """
    if not type(FACILITY_STATIONS) is list:
        raise Exception("Error loading facility station map: not a list")

    return station_name not in FACILITY_STATIONS
