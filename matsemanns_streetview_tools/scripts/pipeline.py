import click
import json
import shutil
import traceback
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from PIL import Image
from tqdm import tqdm

from matsemanns_streetview_tools import gpx, metadata, tracer
from matsemanns_streetview_tools.gpx import GpxTrack, GpxPoint
from matsemanns_streetview_tools.image import apply_image_pipeline, create_exif_data, create_xmp_pano_data
from matsemanns_streetview_tools.util import log, add_file_logger
from matsemanns_streetview_tools.video import calculate_frames_to_keep, save_video_frames, join_images_to_video, \
    inject_spatial_data


@dataclass
class PipelineConfig:
    project_name: str
    video_files: [str]  # supports globs
    original_files_folder: str
    gpx_file: str
    output_folder: str
    frame_distance_meters: float
    keep_debug_files: bool | None = None
    video_time_shift_seconds: float | None = None
    video_cut_beginning_seconds: float | None = None
    video_cut_end_seconds: float | None = None
    contrast: float | None = None
    color: float | None = None
    brightness: float | None = None
    sharpness: float | None = None
    nadir: str | None = None



@click.command()
@click.argument("json_file", type=click.Path(exists=True, dir_okay=False))
def pipeline(json_file):
    """
    Run the pipeline on a batch of files.
    JSON_FILE: Path to json file, should match the format of PipelineConfig
    """
    json_path = Path(json_file)
    json_txt = json_path.read_text()
    json_content = json.loads(json_txt)

    config = PipelineConfig(**json_content)
    project_path = json_path.parent

    run_pipeline(project_path, config)



def run_pipeline(project_folder: Path, config: PipelineConfig):
    gpx_track = gpx.read_gpx_file(project_folder / config.gpx_file)
    output_folder = project_folder / config.output_folder
    nadir = Image.open(project_folder / config.nadir) if config.nadir else None

    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    add_file_logger(output_folder / "log.txt")

    video_files = []
    for file_or_glob in config.video_files:
        video_files.extend(list(project_folder.glob(file_or_glob)))

    # Sort gopro videos by how they're created
    video_files.sort(key=lambda file: (file.stem[4:], file.stem))

    log(f"========================================================")
    log(f"========================================================")
    log(f"Starting pipeline")
    log(f"{len(video_files)} files found")
    log(video_files)
    log(f"Will save to {output_folder.resolve()}")
    log(f"Config: {config}")

    failed_videos = []

    for video_file in tqdm(video_files, desc="Files"):
        try:
            original_file = project_folder / config.original_files_folder / (video_file.stem + ".360")
            run_pipeline_on_file(video_file, original_file, gpx_track, output_folder, config, nadir)
        except Exception as e:
            failed_videos.append(video_file)
            log(f"ERROR: File {video_file} FAILED due to {e}\n{traceback.format_exc()}")

    log(tracer.out())
    log(f"Failed videos ({len(failed_videos)}): {failed_videos}")
    log("ALL DONE!")


def run_pipeline_on_file(
        video_file: Path,
        original_file: Path,
        gpx_track: GpxTrack,
        output_folder: Path,
        config: PipelineConfig,
        nadir: Image.Image | None
):
    log("====================================")
    log(f"Working on file {video_file.name}")

    with tracer.trace("exiftoolmeta"):
        log(f"Finding metadata of 360 file {original_file}")
        original_metadata = metadata.get_exiftool_metadata(original_file)
    with tracer.trace("ffprobe"):
        log(f"Finding metadata of equirectangular file {video_file}")
        equi_metadata = metadata.get_ffprobe_metadata(video_file)

    log("Calculating times to use in the video")

    # Find the start time of the video, but shift it if needed to
    # match the gpx file
    video_time_shift = timedelta(seconds=config.video_time_shift_seconds or 0)
    video_original_start = original_metadata.get_embedded_gpx_start_time()
    video_start = video_original_start + video_time_shift
    video_end = video_start + equi_metadata.get_duration()

    # It's the gpx file that controls the frames we extract. So crop it to match
    # the video, and also include if we want to drop the beginning/end of the video
    video_cut_beginning = timedelta(seconds=config.video_cut_beginning_seconds or 0)
    video_cut_end = timedelta(seconds=config.video_cut_end_seconds or 0)
    first_frame = video_start + video_cut_beginning
    last_frame = video_end - video_cut_end
    duration = last_frame - first_frame

    log(f"Video gpx starts at {video_original_start}, shifted to {video_start} and ends at {video_end}, duration {equi_metadata.get_duration()}")
    log(f"First frame will be at {first_frame}, last at {last_frame} for a duration of {duration}")

    log("Creating the gpx tracks")
    cropped_gpx = gpx.crop_with_interpolation(gpx_track, first_frame, duration)
    spaced_gpx = gpx.space_out_points(cropped_gpx, spacing_distance_m=Decimal(config.frame_distance_meters))

    log(f"Gpx for video had {len(cropped_gpx.points)} points, after spacing out every {config.frame_distance_meters}m it's {len(spaced_gpx.points)} points")

    # Space each point out 1 second to match the finished video
    project_final_name = f"{video_file.stem}{"_" if config.project_name else ""}{config.project_name}"
    video_gpx = gpx.adjust_time(spaced_gpx, first_frame, timedelta(seconds=1))
    gpx_out_file = output_folder / f"{project_final_name}.gpx"
    log(f"Writing gpx file to be used with video to {gpx_out_file}")
    gpx_out_file.write_text(gpx.gpx_track_to_xml(video_gpx))

    log("Calculating frames to keep")
    frames = calculate_frames_to_keep(
        spaced_gpx,
        video_start,
        video_end,
        equi_metadata.get_framerate()
    )

    extract_folder = output_folder / f"{video_file.stem}_extracted"
    log(f"Found {len(frames)} frames to extract, extracting into {extract_folder}")
    with tracer.trace("extract frames"):
        save_video_frames(video_file, extract_folder, frames, cleanup=not config.keep_debug_files)


    log("Adding effects and nadir to extracted images")
    saved_frames = [
        extract_folder / f"{video_file.stem}-{i:06}.jpg" for i, f in enumerate(frames, start=1)
    ]
    save_image_folder = output_folder / f"{video_file.stem}"
    if not save_image_folder.exists():
        save_image_folder.mkdir()

    new_images = []

    for (image_path, gpx_point) in tqdm(zip(saved_frames, spaced_gpx.points), desc="Applying image pipeline", total=len(saved_frames), leave=True):
        with tracer.trace("image pipeline"):
            image = Image.open(image_path)
            updated_image = apply_image_pipeline(image, nadir,
                                 color=config.color,
                                 contrast=config.contrast,
                                 brightness=config.brightness,
                                 sharpness=config.sharpness)
            exif = create_exif_data(updated_image, gpx_point)
            xmp_data = create_xmp_pano_data(updated_image)
            image_out = save_image_folder / image_path.name
            new_images.append(image_out)
            updated_image.save(image_out, quality=95, exif=exif, xmp=xmp_data)

    tmp_video = output_folder / f"{video_file.stem}_tmp.mp4"
    log(f"Joining images back to video, into {tmp_video}")

    with tracer.trace("joining images"):
        join_images_to_video(new_images, tmp_video, metadata_create_time=first_frame, framerate=1, cleanup=not config.keep_debug_files)

    log("Injecting 360 metadata into final video")
    final_video = output_folder / f"{project_final_name}.mp4"
    with tracer.trace("inject spatial"):
        inject_spatial_data(tmp_video, final_video)

    if not config.keep_debug_files:
        log("Cleaning up")
        tmp_video.unlink(missing_ok=True)
        shutil.rmtree(extract_folder)

    log(f"Done! Video at {final_video}, gpx file at {gpx_out_file}, images at {save_image_folder}")

