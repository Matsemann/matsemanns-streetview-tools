import dataclasses
from datetime import datetime, timedelta
from decimal import Decimal

from . import GpxTrack
from ._math import relative_distance, eucl, intersect_line_with_circle, interpolate_gpx_points, get_angle_degrees


def crop_with_interpolation(track: GpxTrack, start_time: datetime, duration: timedelta) -> GpxTrack:
    """Takes a GpxTrack, and crops it so that it starts and ends the given time.
    If the times don't match exactly a point in the track, it will be interpolated between
     the points before and after."""

    end_time = start_time + duration

    if track.points[0].utc_time > end_time or track.points[-1].utc_time < start_time:
        raise RuntimeError(f"No overlap between gpx and time period. "
                           f"Gpx: {track.points[0].utc_time}-{track.points[-1].utc_time} "
                           f"Crop time: {start_time}-{end_time}")

    # Find first point in track after the start time
    first_index, first_point = next((i, p) for i, p in enumerate(track.points) if p.utc_time >= start_time)

    if first_index == 0 or first_point.utc_time == start_time:
        # just keep point as is
        start_point = first_point
        start_index = first_index + 1
    else:
        # interpolate between two points
        prev_point = track.points[first_index - 1]
        prev_to_start = Decimal((start_time - prev_point.utc_time).total_seconds())
        prev_to_point = Decimal((first_point.utc_time - prev_point.utc_time).total_seconds())
        fraction = (prev_to_start / prev_to_point)

        start_point = interpolate_gpx_points(prev_point, first_point, fraction)
        start_index = first_index  # as the point we found should be included later

    # Find first point in track after the end time
    last_index, last_point = next(((i, p) for i, p in enumerate(track.points) if p.utc_time >= end_time), (None, None))

    if last_index is None or last_point is None:
        # Gpx track ends before, just keep end point
        # (really, both are always none or not at the same time)
        end_point = track.points[-1]
        end_index = len(track.points) - 1
    elif last_point.utc_time == end_time:
        # Keep as is
        end_point = last_point
        end_index = last_index
    else:
        # interpolate between two points
        prev_point = track.points[last_index - 1]
        prev_to_end = Decimal((end_time - prev_point.utc_time).total_seconds())
        prev_to_point = Decimal((last_point.utc_time - prev_point.utc_time).total_seconds())
        fraction = (prev_to_end / prev_to_point)

        end_point = interpolate_gpx_points(prev_point, last_point, fraction)
        end_index = last_index  # the point found shouldn't be included

    points = [start_point] + track.points[start_index:end_index] + [end_point]

    return GpxTrack(
        name=track.name,
        utc_time=points[0].utc_time,
        points=points
    )


def space_out_points(track: GpxTrack, spacing_distance_m: Decimal) -> GpxTrack:
    """Takes a GpxTrack, and returns a new one where all the points are exactly
    'spacing_distance' in meters apart from each other.

    For instance: if the points form a straight line and are 2 meters apart, and you ask this
    function to space out by 5 meters. Then the first point will be kept at 0m. Point2 is 2m away and will
    be discarded, same for point3 that's 4 meters away. Point4 is 6 meters away, so it's too far. So we calculate
    a new point inbetween point3 and point4 that's 5m away from point1, and keep that. The new point will have
    the correct interpolated time as to when that was passed, based on the times for point3 and point4.
    See tests for more examples.

    So the points and their positions and times will be realistic and match the original gpx, just always
    the correct amount of meters apart.
    """
    points = track.points.copy()

    current_point = points.pop(0)
    # If we need to jump multiple points to reach the
    # distance, we have to interpolate between the last two
    prev_point = current_point

    new_track_points = [current_point]

    # Have to calculate heading of first point manually
    if len(points) > 1:
        # By def we're at 0,0 now
        posx, posy = relative_distance(current_point, points[0])
        current_point.heading = get_angle_degrees(posx, posy)

    while len(points) > 0:
        point = points.pop(0)
        posx, posy = relative_distance(current_point, point)
        distance_from_current_point = eucl(posx, posy)

        if distance_from_current_point < spacing_distance_m:
            # Not far enough yet, try the next point and remember this point
            prev_point = point
            continue

        # Far enough away to make a new point, but possibly too far
        # So figure out exactly when between the last two points we actually
        # were the correct distance away
        prevx, prevy = relative_distance(current_point, prev_point)
        t1, t2 = intersect_line_with_circle((prevx, prevy), (posx, posy), spacing_distance_m)
        t = t1  # if 0 <= t1 <= 1 else t2, think t1 is always what we want no matter what..

        my_point = interpolate_gpx_points(prev_point, point, t)

        # Heading is calculated on the original points as otherwise information
        # is lost, and it may actually point wrong for larger distances
        my_point.heading = get_angle_degrees(posx - prevx, posy - prevy)

        new_track_points.append(my_point)
        prev_point = my_point
        current_point = my_point

        # Might need multiple new points to reach the point, so
        # must check the gpx point again against the current created one
        points.insert(0, point)

    return GpxTrack(
        name=track.name,
        utc_time=new_track_points[0].utc_time,
        points=new_track_points
    )


def adjust_time(track: GpxTrack, start_time: datetime, delta: timedelta) -> GpxTrack:
    """Returns a new GpxTrack with the same points, but where
    the times have been adjusted. First point will be at start_time,
    the next point start_time+delta etc.

    Mainly to make a GpxTrack match pictures converted into a video."""

    points = []

    for i, point in enumerate(track.points):
        new_time = start_time + i * delta
        new_point = dataclasses.replace(point, utc_time=new_time)
        points.append(new_point)

    return dataclasses.replace(
        track,
        utc_time=start_time,
        points=points)

# with open("../test_files/garmin.gpx") as file:
#     gpx_content = file.read()
#     gpx_points = parse_gpx(gpx_content)
#     new_points = distances(gpx_points, Decimal(2))
#     gpx_str = gpx_track_to_xml(new_points)
#
#     with open("../test_files/garmin_2m_out.gpx", mode="w") as out:
#         out.writelines(gpx_str)
