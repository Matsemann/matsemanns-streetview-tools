import click

from .image import image
from .pipeline import pipeline


@click.group()
def cli():
    pass

cli.add_command(image)
cli.add_command(pipeline)