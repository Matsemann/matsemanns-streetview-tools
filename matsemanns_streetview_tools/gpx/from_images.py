from decimal import Decimal

from matsemanns_streetview_tools.gpx import GpxTrack, GpxPoint
from matsemanns_streetview_tools.util import exif_date_to_datetime, log


def gpx_from_image_files(exif_data: list[dict[str, any]]) -> tuple[list[str], GpxTrack]:
    sorted_data = sorted(exif_data, key=lambda d: exif_date_to_datetime(d["GPSDateTime"]) if d.get("GPSDateTime") else 0)

    images = []
    points = []

    for data in sorted_data:
        img = data.get("SourceFile")

        gps_dt = data.get("GPSDateTime")
        gps_lat = data.get("GPSLatitude")
        gps_lon = data.get("GPSLongitude")
        if not gps_dt or not gps_lat or not gps_lon:
            log(f"Image {img} misses exif gps data and will be skipped")
            continue

        if data.get("GPSLatitudeRef") != "N" or data.get("GPSLongitudeRef") != "E":
            log(f"Can't handle positions in this format, only NE supported, was {data.get("GPSLatitudeRef")}{data.get("GPSLongitudeRef")}, image {img}")
            continue

        gps_alt = data.get("GPSAltitude", 0)
        gps_alt_ref = data.get("GPSAltitudeRef")
        if gps_alt_ref is not None and gps_alt_ref != 0:
            log(f"Can't handle below see level, skipping elevation data for {img}")
            gps_alt = 0

        if data.get("GPSImgDirectionRef") == "T":
            gps_bearing = data.get("GPSImgDirection")
        elif data.get("GPSDestBearingRef") == "T":
            gps_bearing = data.get("GPSDestBearing")
        else:
            gps_bearing = None

        time = exif_date_to_datetime(gps_dt)
        lat = Decimal(gps_lat)
        lon = Decimal(gps_lon)

        ele = Decimal(gps_alt)
        heading = Decimal(gps_bearing) if gps_bearing is not None else None

        point = GpxPoint(
            lat=lat, lon=lon, ele=ele, utc_time=time, heading=heading
        )
        images.append(img)
        points.append(point)

    track = GpxTrack(name="matsemanns_streetview_tools track from folder of images",
                     utc_time=points[0].utc_time,
                     points=points)

    return images, track
