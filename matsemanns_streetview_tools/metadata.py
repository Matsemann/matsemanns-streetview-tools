import json
import subprocess
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from matsemanns_streetview_tools.util import (
    log,
    exif_date_to_datetime,
    ffprobe_path,
    exiftool_path,
)


class ExiftoolMetadata:
    def __init__(self, data):
        self.data = data

    def get_embedded_gpx_start_time(self) -> Optional[datetime]:
        gpx_time = self.data.get("GPSDateTime", None)
        if not gpx_time:
            return None
        return exif_date_to_datetime(gpx_time)


def get_exiftool_metadata(file: Path) -> ExiftoolMetadata:
    cmd = [
        exiftool_path(),
        "-api",
        "largefilesupport=1",
        "-ee",
        "-j",
        str(file.resolve()),
    ]
    log(f"Running exiftool: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError("Error from exiftool", proc.stderr)

    result = proc.stdout
    return ExiftoolMetadata(json.loads(result)[0])


def get_exiftool_metadata_for_images_in_folder(folder: Path) -> list[dict[str, Any]]:
    cmd = [exiftool_path(), "-j", "-n", str(folder.resolve())]
    log(f"Running exiftool: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError("Error from exiftool", proc.stderr)

    result = proc.stdout
    return json.loads(result)


class FfprobeMetadata:
    def __init__(self, data):
        self.data = data

    def get_duration(self) -> timedelta:
        duration = self.data["format"]["duration"]
        return timedelta(seconds=float(duration))

    def get_creation_time(self) -> datetime:
        creation_time = self.data["format"]["tags"]["creation_time"]
        return datetime.fromisoformat(creation_time)

    def get_video_stream(self):
        video_stream = next(
            (
                stream
                for stream in self.data["streams"]
                if stream["codec_type"] == "video"
            ),
            None,
        )

        if not video_stream:
            raise RuntimeError("No video stream found")

        return video_stream

    def get_framerate(self) -> Decimal:
        video_stream = self.get_video_stream()

        fps = video_stream["avg_frame_rate"].split("/")

        return Decimal(float(fps[0]) / float(fps[1]))

    def get_video_size(self) -> tuple[int, int]:
        video_stream = self.get_video_stream()

        return int(video_stream["width"]), int(video_stream["height"])


def get_ffprobe_metadata(file: Path) -> FfprobeMetadata:
    cmd = [
        ffprobe_path(),
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file.resolve()),
    ]
    log(f"Running ffprobe: {' '.join(cmd)}")

    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError("Error from ffprobe", proc.stderr)

    result = proc.stdout
    return FfprobeMetadata(json.loads(result))
