"""Decoding for Google-style encoded polylines, and distance along a path.

Some tenants (e.g. Audi) report a flat Distance of 0 on every trip but still
populate the trip's Polyline, so the distance travelled can be recovered from
the GPS path instead.
"""
import math

# IUGG mean Earth radius.
EARTH_RADIUS_METERS = 6371008.8

METERS_PER_MILE = 1609.344


def decode(encoded: str, precision: int = 5) -> list:
    """Decode an encoded polyline into a list of (lat, lng) tuples."""
    if not encoded:
        return []

    index = 0
    lat = 0
    lng = 0
    coordinates = []
    factor = 10 ** precision
    length = len(encoded)

    while index < length:
        for is_latitude in (True, False):
            shift = 0
            result = 0
            while True:
                if index >= length:
                    # Truncated payload - drop the incomplete coordinate.
                    return coordinates
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_latitude:
                lat += delta
            else:
                lng += delta
        coordinates.append((lat / factor, lng / factor))

    return coordinates


def haversine_meters(point_a: tuple, point_b: tuple) -> float:
    """Great-circle distance between two (lat, lng) points, in meters."""
    lat1, lng1 = point_a
    lat2, lng2 = point_b
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (math.sin(delta_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def path_distance_meters(encoded: str, precision: int = 5) -> float:
    """Total distance along an encoded polyline, in meters.

    Returns 0.0 for an empty, unusable, or single-point path. This is a
    GPS-sampled approximation and will read slightly short of a true odometer.
    """
    points = decode(encoded, precision)
    if len(points) < 2:
        return 0.0

    return sum(haversine_meters(points[i - 1], points[i])
               for i in range(1, len(points)))
