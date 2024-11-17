from decimal import Decimal
from datetime import datetime, timezone, timedelta

from pytest import approx, raises

from matsemanns_streetview_tools.gpx import GpxPoint, GpxTrack
from matsemanns_streetview_tools.gpx._math import relative_distance, eucl
from matsemanns_streetview_tools.gpx.modify import (
    crop_with_interpolation,
    space_out_points,
    adjust_time,
)
from matsemanns_streetview_tools.gpx.tests.test_utils import gpx_point


def test_crop_with_interpolation():
    start_time = datetime(2023, 9, 27, 15, 19, 0, tzinfo=timezone.utc)

    points = [
        GpxPoint(
            lat=Decimal(1), lon=Decimal(11), ele=Decimal(1001), utc_time=start_time
        ),
        GpxPoint(
            lat=Decimal(2),
            lon=Decimal(12),
            ele=Decimal(1002),
            utc_time=start_time + timedelta(seconds=5),
        ),
        GpxPoint(
            lat=Decimal(3),
            lon=Decimal(13),
            ele=Decimal(1003),
            utc_time=start_time + timedelta(seconds=10),
        ),
        GpxPoint(
            lat=Decimal(4),
            lon=Decimal(14),
            ele=Decimal(1004),
            utc_time=start_time + timedelta(seconds=15),
        ),
        GpxPoint(
            lat=Decimal(5),
            lon=Decimal(15),
            ele=Decimal(1005),
            utc_time=start_time + timedelta(seconds=20),
        ),
    ]

    track = GpxTrack(name="test track", utc_time=start_time, points=points)

    # Crop exactly everything, exact:
    crop = crop_with_interpolation(
        track, start_time=start_time, duration=timedelta(seconds=20)
    )
    assert len(crop.points) == 5
    assert crop.points[0] == points[0]
    assert crop.points[4] == points[4]

    # Crop from point 2 to 4, exact (no interpolation):
    crop = crop_with_interpolation(
        track,
        start_time=start_time + timedelta(seconds=5),
        duration=timedelta(seconds=10),
    )
    assert len(crop.points) == 3
    assert crop.points[0] == points[1]
    assert crop.points[2] == points[3]

    # Crop from a bit before gpx start until a bit before gpx end
    # should then just keep first point, and interpolate last between point
    # two and three
    crop = crop_with_interpolation(
        track,
        start_time=start_time + timedelta(seconds=-10),
        duration=timedelta(seconds=17.5),
    )
    assert len(crop.points) == 3
    assert crop.points[0] == points[0]
    assert crop.points[1] == points[1]
    assert crop.points[2].utc_time == start_time + timedelta(seconds=7.5)
    assert crop.points[2].lat == Decimal("2.5")
    assert crop.points[2].lon == Decimal("12.5")

    # Crop until long after gpx track, should then just keep last point
    # Plus interpolate first point
    crop = crop_with_interpolation(
        track,
        start_time=start_time + timedelta(seconds=2.5),
        duration=timedelta(seconds=100),
    )
    assert len(crop.points) == 5
    assert crop.points[0].lat == Decimal("1.5")
    assert crop.points[4] == points[4]

    # Ask for a crop outside gpx track, should raise exception
    with raises(RuntimeError):
        crop_with_interpolation(
            track,
            start_time=start_time - timedelta(seconds=100),
            duration=timedelta(seconds=90),
        )


def test_space_out_points():
    lat = Decimal("59.9298520")
    lon = Decimal("10.7918700")
    diff = 2 / Decimal(111300)  # about 2m

    start_time = datetime(2023, 9, 27, 15, 19, 0, tzinfo=timezone.utc)

    points = []

    # 10 points, 2m away from each other 1 second apart
    for i in range(10):
        points.append(
            GpxPoint(
                lat=lat + (i * diff),
                lon=lon,
                ele=Decimal(0),
                utc_time=start_time + timedelta(seconds=i),
            )
        )

    track = GpxTrack(name="dummy", utc_time=points[0].utc_time, points=points)
    new_track = space_out_points(track, spacing_distance_m=Decimal("5"))

    # Ended up with only 4 points
    assert len(new_track.points) == 4
    # First point remains the same
    assert new_track.points[0] == points[0]
    # Second point is 5 meters away
    x, y = relative_distance(new_track.points[0], new_track.points[1])
    assert eucl(x, y) == Decimal("5")
    # Second point's time is interpolated between original times
    assert new_track.points[1].utc_time == start_time + timedelta(seconds=2.5)


def test_space_out_points_correct_heading():
    """
    See intersect_heading.png,
    basically we want the heading to not be
    calculated as the heading of the new gpx track (the red line),
    but from the original points with more information about the actual
    heading at that time.
    """
    one_meter = 1 / Decimal(111300)  # about 1m at 0,0
    error_diff = one_meter / 10000

    point1 = gpx_point(lon=Decimal(0), lat=Decimal(0))
    point2 = gpx_point(lon=3 * one_meter, lat=Decimal(0))
    point3 = gpx_point(lon=5 * one_meter, lat=6 * one_meter)
    point4 = gpx_point(lon=10 * one_meter, lat=6 * one_meter)

    track = GpxTrack(
        name="dummy", utc_time=point1.utc_time, points=[point1, point2, point3, point4]
    )

    new_track = space_out_points(track, spacing_distance_m=Decimal("5"))

    assert new_track.points[0].heading == approx(Decimal(90), Decimal(0.01))

    assert new_track.points[1].lon == approx(one_meter * 4, error_diff)
    assert new_track.points[1].lat == approx(one_meter * 3, error_diff)
    assert new_track.points[1].heading == approx(Decimal("18.4349489"), Decimal(0.01))

    assert new_track.points[2].lon == approx(one_meter * 8, error_diff)
    assert new_track.points[2].lat == approx(one_meter * 6, error_diff)
    assert new_track.points[2].heading == approx(Decimal(90), Decimal(0.01))


def test_adjust_time():
    start_time = datetime(2023, 9, 27, 15, 19, 33, 0, tzinfo=timezone.utc)
    delta = timedelta(milliseconds=200)

    track = GpxTrack(
        name="dummy",
        utc_time=datetime(2023, 1, 1, 1, 1, 1, 1, tzinfo=timezone.utc),
        points=[
            gpx_point(utc_time=datetime(2023, 1, 1, 1, 1, 1, 1, tzinfo=timezone.utc)),
            gpx_point(utc_time=datetime(2023, 1, 2, 1, 1, 1, 1, tzinfo=timezone.utc)),
            gpx_point(utc_time=datetime(2023, 1, 3, 1, 1, 1, 1, tzinfo=timezone.utc)),
        ],
    )

    new_track = adjust_time(track=track, start_time=start_time, delta=delta)

    assert new_track.points[0].utc_time == datetime(
        2023, 9, 27, 15, 19, 33, 0, tzinfo=timezone.utc
    )
    assert new_track.points[1].utc_time == datetime(
        2023, 9, 27, 15, 19, 33, 200_000, tzinfo=timezone.utc
    )
    assert new_track.points[2].utc_time == datetime(
        2023, 9, 27, 15, 19, 33, 400_000, tzinfo=timezone.utc
    )
