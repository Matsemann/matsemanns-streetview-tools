import subprocess
from decimal import Decimal
from datetime import datetime
from typing import Iterable

from math import ceil
from pathlib import Path

from tqdm import tqdm

from matsemanns_streetview_tools.gpx import GpxTrack
from matsemanns_streetview_tools.util import log, ffmpeg_path


def calculate_frames_to_keep(
    track: GpxTrack,
    video_start_time: datetime,
    video_end_time: datetime,
    video_fps: Decimal,
) -> list[int]:
    """Calculates the frame number in the video for each point in the track.
    Mainly to be used with a spaced track, to find the correct video frame
    for each point.

    The video_start_time is the (gpx shifted) start time of the video that the timings
    of the gpx points will be in relation to (so if video start is 12:00:05, and first
    gpx point is 12:00:15, the first video frame to keep will be after 10 seconds).

    All points need to be withing the video times, use the gpx cropper first to control
    what is included from the video.
    """

    frames = []

    for point in track.points:
        if video_start_time <= point.utc_time <= video_end_time:
            seconds_since_start = (point.utc_time - video_start_time).total_seconds()
            frame = ceil(seconds_since_start * float(video_fps))
            frames.append(frame)
        else:
            raise RuntimeError("Gpx contains points outside video, crop it first")

    return frames


def _create_ffmpeg_frame_file_content(frames: list[int]) -> str:
    start = "select='"
    end = "'"

    def single_frame(frame: int) -> str:
        return f"+eq(n,{frame})"

    content = "\n".join(single_frame(frame) for frame in frames)

    return start + content + end


def run_ffmpeg_with_progress(ffmpeg_command: list[str]) -> Iterable[int]:
    """Util for running ffmpeg and get constant progress updates

    The command should include: ["-progress", "-", "-nostats"]
    to give the needed output for this function to work as expected
    """

    log(f"Running ffmpeg: {' '.join(ffmpeg_command)}")

    proc = subprocess.Popen(
        ffmpeg_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    while True:
        code = proc.poll()

        assert proc.stdout
        out = proc.stdout.readline().decode("utf-8")
        # log(out)
        if out.startswith("frame="):
            frame_num = int(out.split("=")[1])
            yield frame_num

        if code is not None:
            log(f"Ffmpeg finished (exit code {code})")
            break

    if proc.returncode != 0:
        assert proc.stderr
        raise RuntimeError("Error from ffmpeg", proc.stderr.readlines())


def save_video_frames(
    video_file: Path,
    output_folder: Path,
    frames: list[int],
    quality: int = 2,
    progressbar: bool = True,
    cleanup: bool = True,
) -> None:
    """Saves the specified frames from the video to the folder,
    quality is a number where 2=best, 4=good, etc.
    """
    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    video_name = video_file.stem

    frames_file = output_folder / f"{video_name}_frames.txt"
    frames_file.write_text(_create_ffmpeg_frame_file_content(frames))

    output_pattern = output_folder / f"{video_name}-%6d.jpg"

    ffmpeg_command = [
        ffmpeg_path(),
        "-i",
        str(video_file.resolve()),
        "-q:v",
        str(quality),
        "-filter_script:v",
        str(frames_file.resolve()),
        "-vsync",
        "0",
        "-progress",
        "-",
        "-nostats",
        str(output_pattern.resolve()),
    ]

    if progressbar:
        with tqdm(
            total=len(frames), desc="Extract frames from video", leave=True
        ) as pbar:
            for frame in run_ffmpeg_with_progress(ffmpeg_command):
                pbar.update(frame - pbar.n)
    else:
        list(run_ffmpeg_with_progress(ffmpeg_command))  # just force the iteration

    if cleanup:
        frames_file.unlink(missing_ok=True)


def _create_ffmpeg_image_content(images: list[Path]) -> str:
    lines = [f"file '{p.resolve()}'" for p in images]
    return "\n".join(lines)


def join_images_to_video(
    images: list[Path],
    output_file: Path,
    metadata_create_time: datetime,
    framerate: int = 1,
    crf_quality: int = 23,
    preset: str = "medium",
    progressbar: bool = True,
    cleanup: bool = True,
) -> None:
    output_folder = output_file.parent
    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    images_file = output_folder / f"{output_file.stem}_images.txt"
    images_file.write_text(_create_ffmpeg_image_content(images))

    time = metadata_create_time.isoformat().replace("+00:00", "Z")

    ffmpeg_command = [
        ffmpeg_path(),
        "-y",  # file might exist..
        "-r",
        str(framerate),
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(images_file.resolve()),
        "-crf",
        str(crf_quality),
        "-preset",
        preset,
        "-metadata",
        f"creation_time={time}",
        "-progress",
        "-",
        "-nostats",
        str(output_file.resolve()),
    ]

    if progressbar:
        with tqdm(total=len(images), desc="Merge images to video", leave=True) as pbar:
            for frame in run_ffmpeg_with_progress(ffmpeg_command):
                # log(f"got frame {frame}")
                pbar.update(frame - pbar.n)
    else:
        list(run_ffmpeg_with_progress(ffmpeg_command))  # just force the iteration

    if cleanup:
        images_file.unlink(missing_ok=True)


def inject_spatial_data(input_file: Path, output_file: Path):
    """Use Googles spatial media injector to inject metadata saying this
    video file should be treated as an equirectangular 360 video"""
    from spatialmedia.metadata_utils import (
        inject_metadata,
        Metadata,
        generate_spherical_xml,
    )

    metadata = Metadata()
    metadata.video = generate_spherical_xml()  # type: ignore
    inject_metadata(input_file, output_file, metadata, log)
    if not output_file.exists():
        raise RuntimeError("Failed injecting spatial metadata, see log")

    # todo or what about exiftool, do a speed check
    # exiftool -api LargeFileSupport=1  -overwrite_original -XMP-GSpherical:Spherical="true" -XMP-GSpherical:Stitched="true" -XMP-GSpherical:StitchingSoftware=dummy -XMP-GSpherical:ProjectionType=equirectangular "$out_dir"/"${base_name}-local.mov"
