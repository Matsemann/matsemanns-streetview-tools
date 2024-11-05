from datetime import datetime
from decimal import Decimal

from matsemanns_streetview_tools.gpx import GpxPoint
from matsemanns_streetview_tools.gpx._math import relative_distance, intersect_line_with_circle, interpolate_value, \
    get_angle_degrees
from pytest import approx

def test_relative_distance():
    p1 = GpxPoint(
        lat=Decimal("20.000000"),
        lon=Decimal("20.000000"),
        ele=Decimal(999),
        utc_time=datetime.now()
    )
    p2 = GpxPoint(
        lat=Decimal("20.000449236"),  # 50m away
        lon=Decimal("20.000449236"),
        ele=Decimal(999),
        utc_time=datetime.now()
    )

    (x, y) = relative_distance(p1, p2)

    assert y.quantize(Decimal(1.00)) == Decimal("50.00")
    assert x < Decimal("47")  # lon is less per degree


def test_intersect_interpolate():
    """
    See intersect.png
    """
    p1 = (Decimal("2"), Decimal("2"))
    p2 = Decimal("5"), Decimal("-5")

    t1, t2 = intersect_line_with_circle(
        p1,
        p2=p2,
        radius=Decimal("5")
    )

    x = interpolate_value(p1[0], p2[0], t1)
    y = interpolate_value(p1[1], p2[1], t1)

    assert x.quantize(Decimal("1.0000")) == Decimal("4.0898")
    assert y.quantize(Decimal("1.0000")) == Decimal("-2.8763")


def test_get_angle_degrees():
    allowed_error = 1 / Decimal(1000)
    assert get_angle_degrees(Decimal(0), Decimal(1)) == approx(Decimal(0), allowed_error)# up
    assert get_angle_degrees(Decimal(0), Decimal(-1)) == approx(Decimal(180), allowed_error)# down
    assert get_angle_degrees(Decimal(1), Decimal(0)) == approx(Decimal(90), allowed_error)# right
    assert get_angle_degrees(Decimal(-1), Decimal(0)) == approx(Decimal(270), allowed_error)# left
    assert get_angle_degrees(Decimal(2), Decimal(6)) == approx(Decimal("18.4349489"), allowed_error)# left up /

