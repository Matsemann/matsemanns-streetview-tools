import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from matsemanns_streetview_tools.metadata import get_exiftool_metadata, ExiftoolMetadata, get_ffprobe_metadata


def test_get_exiftool_metadata():
    # Just testing that it runs
    file = Path("./test_files/GS012187.360")
    meta = get_exiftool_metadata(file)
    assert meta.data["MediaCreateDate"] == "2023:08:17 17:06:25"
    assert meta.get_embedded_gpx_start_time() == datetime(2023, 8, 17, 15, 6, 25, 299000, tzinfo=timezone.utc)
    print(json.dumps(meta.data, indent=1))


def test_get_ffprobe_metadata():
    file = Path("./test_files/GS012187.mp4")
    meta = get_ffprobe_metadata(file)
    print(json.dumps(meta.data, indent=1))
    assert meta.get_duration() == timedelta(seconds=12, milliseconds=712.679)
    assert meta.get_framerate() == 29.97
    assert meta.get_video_size() == (5376, 2688)

