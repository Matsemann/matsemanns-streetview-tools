from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from xml.etree.ElementTree import Element

from .types import GpxTrack, GpxPoint


def parse_gpx(gpx_str: str) -> GpxTrack:
    root = ET.fromstring(gpx_str)
    name = root.find(".//{http://www.topografix.com/GPX/1/1}name")
    trkpts = root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")

    points: list[GpxPoint] = []
    print("")
    for trkpt in trkpts:
        lat = trkpt.attrib["lat"]
        lon = trkpt.attrib["lon"]
        ele: Element | None = trkpt.find(".{http://www.topografix.com/GPX/1/1}ele")
        time: Element | None = trkpt.find(".{http://www.topografix.com/GPX/1/1}time")
        heading: Element | None = trkpt.find(
            "./{http://www.topografix.com/GPX/1/1}extensions/{http://www.topografix.com/GPX/1/1}heading"
        )  # TODO perhaps namespace it better

        assert time is not None and time.text
        utc_time = datetime.fromisoformat(time.text.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )

        points.append(
            GpxPoint(
                lat=Decimal(lat),
                lon=Decimal(lon),
                ele=Decimal(ele.text) if ele is not None and ele.text else Decimal(0),
                utc_time=utc_time,
                heading=Decimal(heading.text)
                if heading is not None and heading.text
                else None,
            )
        )

    return GpxTrack(
        name=name.text if name is not None and name.text else "",
        utc_time=points[0].utc_time,
        points=points,
    )


def read_gpx_file(file: Path) -> GpxTrack:
    gpx_str = file.read_text()
    return parse_gpx(gpx_str)


def gpx_track_to_xml(gpx_track: GpxTrack) -> str:
    points: list[GpxPoint] = gpx_track.points

    def time_to_gpx_str(utc_time: datetime) -> str:
        return utc_time.isoformat().replace("+00:00", "Z")

    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="StravaGPX" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3">
 <metadata>
  <time>{time_to_gpx_str(gpx_track.utc_time)}</time>
 </metadata>
 <trk>
  <name>{gpx_track.name}</name>
  <type>cycling</type>
  <trkseg>"""

    footer = """
  </trkseg>
 </trk>
</gpx>"""

    def point_to_trkpt(point: GpxPoint) -> str:
        extensions = ""
        if point.heading is not None:
            extensions = f"""
    <extensions>
     <heading>{point.heading:.2f}</heading>
    </extensions>"""
        return f"""
   <trkpt lat="{point.lat:.7f}" lon="{point.lon:.7f}">
    <ele>{point.ele:.1f}</ele>
    <time>{time_to_gpx_str(point.utc_time)}</time>{extensions}
   </trkpt>"""

    pts = "".join(point_to_trkpt(p) for p in points)

    return header + pts + footer
