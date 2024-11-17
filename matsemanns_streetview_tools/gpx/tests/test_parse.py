from datetime import datetime, timezone
from decimal import Decimal

from matsemanns_streetview_tools.gpx import (
    parse_gpx,
    GpxTrack,
    GpxPoint,
    gpx_track_to_xml,
)

test_track = """<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="StravaGPX" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3">
 <metadata>
  <time>2023-08-17T14:02:27Z</time>
 </metadata>
 <trk>
  <name>Ring 4 Streetview edition</name>
  <type>cycling</type>
  <trkseg>
   <trkpt lat="59.9298520" lon="10.7918700">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:27Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>162</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9298880" lon="10.7919170">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:28Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9299280" lon="10.7919480">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:29Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9299630" lon="10.7919920">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:30Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9299970" lon="10.7920460">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:31Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9300280" lon="10.7920770">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:32Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9300650" lon="10.7921240">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:33Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9301110" lon="10.7921310">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:34Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>161</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9301580" lon="10.7921450">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:35Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>160</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9302000" lon="10.7922070">
    <ele>111.6</ele>
    <time>2023-08-17T14:02:36Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>160</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9302380" lon="10.7922540">
    <ele>111.6</ele>
    <time>2023-08-17T14:02:37Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>159</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9302740" lon="10.7923040">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:38Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>159</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
   <trkpt lat="59.9303070" lon="10.7923560">
    <ele>111.4</ele>
    <time>2023-08-17T14:02:39Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:atemp>29</gpxtpx:atemp>
      <gpxtpx:hr>159</gpxtpx:hr>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>
  </trkseg>
 </trk>
</gpx>

"""


def test_parse_gpx():
    gpx_track = parse_gpx(test_track)

    assert gpx_track.name == "Ring 4 Streetview edition"
    assert len(gpx_track.points) == 13
    assert gpx_track.points[0].lat == Decimal("59.9298520")
    assert gpx_track.points[0].lon == Decimal("10.7918700")
    assert gpx_track.points[0].ele == Decimal("111.4")


def test_gpx_track_to_xml():
    track = GpxTrack(
        name="test track",
        utc_time=datetime(2023, 9, 25, 11, 12, 13, 999, tzinfo=timezone.utc),
        points=[
            GpxPoint(
                lat=Decimal("11.111"),
                lon=Decimal("22.222"),
                ele=Decimal("999"),
                utc_time=datetime(2023, 9, 25, 11, 12, 13, 999, tzinfo=timezone.utc),
            ),
            GpxPoint(
                lat=Decimal("11.111"),
                lon=Decimal("22.222"),
                ele=Decimal("999"),
                heading=Decimal("123.456"),
                utc_time=datetime(2023, 9, 25, 11, 12, 14, 999, tzinfo=timezone.utc),
            ),
        ],
    )

    xml = gpx_track_to_xml(track)
    assert (
        xml
        == """<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="StravaGPX" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3">
 <metadata>
  <time>2023-09-25T11:12:13.000999Z</time>
 </metadata>
 <trk>
  <name>test track</name>
  <type>cycling</type>
  <trkseg>
   <trkpt lat="11.1110000" lon="22.2220000">
    <ele>999.0</ele>
    <time>2023-09-25T11:12:13.000999Z</time>
   </trkpt>
   <trkpt lat="11.1110000" lon="22.2220000">
    <ele>999.0</ele>
    <time>2023-09-25T11:12:14.000999Z</time>
    <extensions>
     <heading>123.46</heading>
    </extensions>
   </trkpt>
  </trkseg>
 </trk>
</gpx>"""
    )
