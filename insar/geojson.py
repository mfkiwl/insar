"""
Takes in a geojson polygon, outputs bounds to use for dem download
Used with http://geojson.io to get a quick geojson polygon
Coordinates are (lon, lat)
Output: left, bottom, right, top (floats)
"""

import sys
import itertools
import json


def read_json(input_string):
    """Loads a json_dict from either a filename or a json string

    Args:
        geojson (str): either path to file, or full parsable string

    Returns:
        dict: json loaded into a dict
    """
    if '{' in input_string:
        # Assuming not a filename:
        json_dict = json.loads(input_string)
    else:
        with open(input_string, 'r') as f:
            json_dict = json.load(f)
    return json_dict


def parse_coordinates(geojson):
    """Finds the coordinates of a geojson polygon

    Note: we are assuming one simple polygon with no holes

    Args:
        geojson (dict): loaded geojson dict

    Returns:
        list: coordinates of polygon in the geojson

    Raises:
        KeyError: if invalid geojson type (no 'geometry' in the json)
        AssertionError: if the geojson 'type' is not 'Polygon'
    """
    # First, if given a deeper object (e.g. from geojson.io), extract just polygon
    try:
        if geojson.get('type') == 'FeatureCollection':
            geojson = geojson['features'][0]['geometry']
        elif geojson.get('type') == 'Feature':
            geojson = geojson['geometry']
    except KeyError:
        print("Invalid geojson")
        raise

    assert geojson['type'] == 'Polygon', 'Must use polygon geojson'
    return geojson['coordinates'][0]


def bounding_box(geojson):
    """From a geojson object, compute bounding lon/lats

    Valid geojson types: Polygon (necessary at some depth), Feature, FeatureCollection

    Args:
        geojson (dict): json pre-loaded into a dict

    Returns:
        tuple[float]: the left,bottom,right,top bounding box of the Polygon
    """
    geojson = read_json(geojson) if isinstance(geojson, str) else geojson

    coordinates = parse_coordinates(geojson)

    left = min(float(lon) for (lon, lat) in coordinates)
    right = max(float(lon) for (lon, lat) in coordinates)

    top = max(float(lat) for (lon, lat) in coordinates)
    bottom = min(float(lat) for (lon, lat) in coordinates)
    return left, bottom, right, top


def print_coordinates(geojson_dict):
    """Prints out the lon,lat points in the polygon joined in one string

    Used for ASF API queries: https://www.asf.alaska.edu/get-data/learn-by-doing/
    E.g. (from their example api request, the following URL params are used)
    polygon=-155.08,65.82,-153.5,61.91,-149.50,63.07,-149.94,64.55,-153.28,64.47,-155.08,65.82

    Args:
        geojson (dict): json pre-loaded into a dict

    Returns:
        str: lon,lat points of the Polygon in order as 'lon1,lat1,lon2,lat2,...'
    """
    c = parse_coordinates(geojson_dict)
    return ','.join(str(coord) for coord in itertools.chain.from_iterable(c))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        json_dict = read_json(sys.argv[1])
    else:
        json_dict = read_json(sys.stdin.read())

    print(print_coordinates(json_dict))
    print(' '.join(str(c) for c in bounding_box(json_dict)))
