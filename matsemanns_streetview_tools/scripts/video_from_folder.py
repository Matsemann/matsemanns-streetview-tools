from datetime import timedelta
from pathlib import Path

import click

from matsemanns_streetview_tools import gpx
from matsemanns_streetview_tools.metadata import (
    get_exiftool_metadata_for_images_in_folder,
)
from matsemanns_streetview_tools.util import log
from matsemanns_streetview_tools.video import join_images_to_video, inject_spatial_data


@click.command()
@click.argument(
    "image_folder", type=click.Path(exists=True, dir_okay=True, file_okay=False)
)
@click.argument("out_folder", type=click.Path(dir_okay=True, file_okay=False))
def video_from_folder(image_folder: str, out_folder: str) -> None:
    images_path = Path(image_folder)
    output_folder = Path(out_folder)

    if not output_folder.exists():
        output_folder.mkdir(parents=True)

    log("Finding gps points from images")
    exif_data = get_exiftool_metadata_for_images_in_folder(images_path)
    images, gpx_track = gpx.gpx_from_image_files(exif_data)

    video_creation_time = gpx_track.utc_time.replace(microsecond=0)

    # Space the points out 1 second each to match the generated video
    video_gpx = gpx.adjust_time(
        gpx_track, start_time=video_creation_time, delta=timedelta(seconds=1)
    )
    gpx_out_file = output_folder / f"{images_path.stem}.gpx"
    log(f"Writing gpx file to be used with video to {gpx_out_file}")
    gpx_out_file.write_text(gpx.gpx_track_to_xml(video_gpx))

    log("Joining images to video")
    tmp_video = output_folder / f"{images_path.stem}_temp.mp4"
    image_paths = [Path(img) for img in images]
    join_images_to_video(
        image_paths, tmp_video, metadata_create_time=video_creation_time, framerate=1
    )

    log("Injecting 360 metadata into final video")
    final_video = output_folder / f"{images_path.stem}.mp4"
    inject_spatial_data(tmp_video, final_video)
    tmp_video.unlink(missing_ok=True)

    log(f"Done! Video at {final_video}, gpx file at {gpx_out_file}")
