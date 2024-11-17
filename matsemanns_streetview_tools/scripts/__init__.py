import click

from .google import google
from .image import image
from .pipeline import pipeline
from .video_from_folder import video_from_folder


@click.group()
def cli():
    pass

cli.add_command(image)
cli.add_command(pipeline)
cli.add_command(video_from_folder)
cli.add_command(google)
