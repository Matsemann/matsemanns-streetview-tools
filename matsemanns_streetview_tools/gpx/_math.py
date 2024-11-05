import math
from datetime import datetime, timezone
from decimal import Decimal

from matsemanns_streetview_tools.gpx import GpxPoint


def relative_distance(origin: GpxPoint, point: GpxPoint) -> tuple[Decimal, Decimal]:
    """Relative x,y distance in cartesian, relative to origin as (0,0)
    Since the points actually lie on a sphere, it's not exact, but good
    enough for the small distances between two points.

    """
    deglen = 111300  # meters per degree

    yfactor = Decimal(math.cos(math.radians(origin.lat)))
    deglenlon = yfactor * deglen  # m per degree at this lat

    x = (point.lon - origin.lon) * deglenlon
    y = (point.lat - origin.lat) * deglen
    return x, y


def eucl(x, y):
    return math.sqrt(x ** 2 + y ** 2)


def intersect_line_with_circle(p1: tuple[Decimal, Decimal], p2: tuple[Decimal, Decimal], radius: Decimal) -> tuple[
    Decimal, Decimal]:
    """Figure out where a line between the two points intersect with a
    circle with center at origin.

    See intersect.png for an explanation:
    In that image, C is p1 and D is p2, and we're trying to find E.

    OBS: What's returned is the time at which the point was reached when looking at the line
    in parametric form. Not the point itself.
    """
    # https://math.stackexchange.com/a/311956/28786
    a = (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
    b = 2 * (p2[0] - p1[0]) * p1[0] + 2 * (p2[1] - p1[1]) * p1[1]
    c = p1[0] ** 2 + p1[1] ** 2 - radius ** 2

    b24ac = (b ** 2 - 4 * a * c).sqrt()

    t1 = (-b + b24ac) / (2 * a)
    t2 = (-b - b24ac) / (2 * a)

    return t1, t2


def interpolate_value(start: Decimal, end: Decimal, fraction: Decimal) -> Decimal:
    """Fraction should be between 0 (entirely at start) and 1 (entirely at end)"""
    return start + (end - start) * fraction


def interpolate_gpx_points(start: GpxPoint, end: GpxPoint, fraction: Decimal) -> GpxPoint:
    timei = interpolate_value(Decimal(start.utc_time.timestamp()), Decimal(end.utc_time.timestamp()), fraction)

    return GpxPoint(
        lat=interpolate_value(start.lat, end.lat, fraction),
        lon=interpolate_value(start.lon, end.lon, fraction),
        ele=interpolate_value(start.ele, end.ele, fraction),
        utc_time=datetime.fromtimestamp(float(timei), tz=timezone.utc)
    )


def get_angle_degrees(x: Decimal, y: Decimal) -> Decimal:
    """0-360, where 0 is north/up"""
    return (Decimal(
        math.degrees(math.atan2(x, y))
    ) + 360) % 360
