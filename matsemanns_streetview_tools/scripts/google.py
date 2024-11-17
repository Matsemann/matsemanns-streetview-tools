from pathlib import Path
from traceback import print_stack

import click

import matsemanns_streetview_tools.google_street_view as gsv
from matsemanns_streetview_tools import gpx
from matsemanns_streetview_tools.util import log


@click.group()
def google():
    """Tools for Google Street View"""
    pass


@google.command()
def auth():
    """Authorize this app to contact google street view services on your behalf"""
    gsv.authorize()


@google.command()
@click.argument(
    "input_files",
    type=click.Path(exists=True, dir_okay=False),
    nargs=-1,
)
@click.option(
    "--chunk-size",
    type=int,
    default=16,
    help="How much to upload in one request, in MiB, as a multiple of 2.",
)
def upload(input_files, chunk_size):
    """Upload video files, using a gpx track matching the video names.
    Can handle multiple videos or glob expansions from command line"""

    if chunk_size < 2 or chunk_size % 2 != 0:
        log("Chunk size must be a multiple of 2")
        return

    failed_videos = []

    for file in input_files:
        log(f"Uploading {file}")
        video = Path(file)
        gpx_path = video.parent / f"{video.stem}.gpx"
        try:
            if not gpx_path.exists():
                raise RuntimeError(f"Didn't find a gpx file named {gpx_path}")

            gpx_track = gpx.read_gpx_file(gpx_path)
            gsv.upload_streetview_video(
                video,
                gpx_track,
                chunk_size_mib=chunk_size,
            )
        except Exception as err:
            log(f"Something went wrong {err}")
            failed_videos.append(file)

    log("Done!")
    if len(failed_videos) > 0:
        log(f"Some videos failed, {failed_videos}")
