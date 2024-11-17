import itertools
from pathlib import Path

import click
from PIL import Image, ImageDraw, ImageOps

from matsemanns_streetview_tools.image import create_nadir, apply_image_pipeline


@click.group()
def image():
    """Various utils for working with images"""
    pass


@image.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path(dir_okay=False))
@click.option("-w", "--width", type=int, default=5376)
@click.option("-h", "--height", type=int, default=588)
def nadir(input_file, output_file, width, height):
    """Convert a square image to an equirectangular nadir"""
    create_nadir(Path(input_file), Path(output_file), width, height)


@image.command()
@click.argument("input_file", type=click.Path())
def test_effects(input_file):
    """Apply an array of image effects on the image to see how they would look.
    Can then later use the same parameters in the pipeline json config."""

    path = Path(input_file)
    folder = path.parent / path.stem
    if not folder.exists():
        folder.mkdir()

    img = Image.open(input_file)

    contrasts = [0.95, 1.0, 1.05]
    brightness = [1.0, 1.05]
    colors = [1.0, 1.2]
    sharpness = [None]

    for con, bri, col, sharp in itertools.product(
        contrasts, brightness, colors, sharpness
    ):
        img2 = apply_image_pipeline(
            img, contrast=con, color=col, brightness=bri, sharpness=sharp
        )
        ImageDraw.Draw(img2).text(
            (0, 0), f"con={con},bri={bri},col={col},sharp={sharp}", font_size=50
        )
        img2.save(folder / f"con{con}_bri{bri}_col{col}_sharp{sharp}.jpg", quality=95)


@image.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
def show(input_file):
    """Launches a GUI to show the image and apply effects on it.
    Can then later use the same parameters in the pipeline json config.

    Uses dearpygui, if it doesn't work, use the test-effects command instead to generate examples."""
    import dearpygui.dearpygui as dpg

    pil_image = Image.open(input_file)
    pil_image.putalpha(255)
    org_width, org_height = pil_image.size
    pil_image = pil_image.resize(
        (org_width // 2, org_height // 2), Image.Resampling.LANCZOS
    )
    width, height = pil_image.size
    image_data = [value / 255.0 for value in pil_image.tobytes()]
    edited_image_data = image_data

    dpg.create_context()
    dpg.create_viewport(title="Custom Title", width=width + 50, height=height + 300)

    # Create texture in Dear PyGui
    with dpg.texture_registry():
        dpg.add_dynamic_texture(width, height, image_data, tag="image")

    config = {
        "brightness": 1.0,
        "contrast": 1.0,
        "color": 1.0,
    }

    def cb(sender):
        nonlocal edited_image_data
        config[sender] = dpg.get_value(sender)
        new_img = apply_image_pipeline(
            pil_image,
            brightness=config["brightness"],
            contrast=config["contrast"],
            color=config["color"],
        )
        edited_image_data = [value / 255.0 for value in new_img.tobytes()]
        dpg.set_value("original", False)
        dpg.set_value("image", edited_image_data)

    def swap(sender):
        show_original = dpg.get_value(sender)
        if show_original:
            dpg.set_value("image", image_data)
        else:
            dpg.set_value("image", edited_image_data)

    with dpg.window(label="Image editor", width=width + 30, height=height + 290):
        dpg.add_input_float(
            label="brightness",
            default_value=1.0,
            step=0.05,
            min_value=0.5,
            max_value=3,
            callback=cb,
            tag="brightness",
        )
        dpg.add_input_float(
            label="contrast",
            default_value=1.0,
            step=0.05,
            min_value=0.5,
            max_value=3,
            callback=cb,
            tag="contrast",
        )
        dpg.add_input_float(
            label="color",
            default_value=1.0,
            step=0.05,
            min_value=0.5,
            max_value=3,
            callback=cb,
            tag="color",
        )
        dpg.add_selectable(label="Show original", callback=swap, tag="original")
        dpg.add_image("image")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
