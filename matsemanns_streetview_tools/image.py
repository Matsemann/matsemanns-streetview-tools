import subprocess
from os import environ
from pathlib import Path
from PIL import Image, ImageEnhance, ExifTags


from matsemanns_streetview_tools.gpx import GpxPoint
from matsemanns_streetview_tools.util import log, datetime_to_exifdatetime, datetime_to_exifdate


def magick_path() -> None:
    return environ.get('MAGICK_PATH', 'magick')


def create_nadir(input_file: Path, output_file: Path, width: int = 5376, height: int = 588) -> None:


    cmd = [magick_path(),
           str(input_file.resolve()),
           "-rotate", "180",
           "-distort", "DePolar", "0",
           "-rotate", "180",
           "-resize", f"{width}x{height}!",
           str(output_file.resolve())
           ]
    log(f"Running magick: {' '.join(cmd)}")

    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError("Error from magick", proc.stderr)


def apply_image_pipeline(img: Image.Image,
                         nadir: Image.Image | None = None,
                         color: float | None = None,
                         contrast: float | None = None,
                         brightness: float | None = None,
                         sharpness: float | None = None,
                         ) -> Image.Image:
    if contrast:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if brightness:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if color:
        img = ImageEnhance.Color(img).enhance(color)
    if sharpness:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)

    if nadir:
        w, h = img.size
        n_w, n_h = nadir.size
        if w != n_w:
            log(f"Nadir doesn't cover whole image width, nadir is {n_w}x{n_h}, image is {w}x{h}")
        nadir_pos_top = h - n_h
        img.paste(nadir, (0, nadir_pos_top))

    return img  # todo save quality, other quality stuff?

def create_exif_data(img: Image.Image, gpx_point: GpxPoint):
    exif_datetime = datetime_to_exifdatetime(gpx_point.utc_time)
    exif_date = datetime_to_exifdate(gpx_point.utc_time)

    base_data = {
        ExifTags.Base.Software: "matsemanns_streetview_tools",
        ExifTags.Base.DateTimeOriginal: exif_datetime,
        ExifTags.Base.DateTime: exif_datetime,
        ExifTags.Base.DateTimeDigitized: exif_datetime,
    }

    gps_data = {
        ExifTags.GPS.GPSDateStamp: exif_date,
        ExifTags.GPS.GPSLatitudeRef: "N",
        ExifTags.GPS.GPSLatitude: round(gpx_point.lat, 7),
        ExifTags.GPS.GPSLongitudeRef: "E",
        ExifTags.GPS.GPSLongitude: round(gpx_point.lon, 7),
        ExifTags.GPS.GPSAltitudeRef: 0,
        ExifTags.GPS.GPSAltitude: round(gpx_point.ele, 7),
        ExifTags.GPS.GPSDestBearingRef: "T",
        ExifTags.GPS.GPSImgDirectionRef: "T",
        ExifTags.GPS.GPSTimeStamp: (gpx_point.utc_time.hour, gpx_point.utc_time.minute, gpx_point.utc_time.second),
    }

    if gpx_point.heading is not None:
        gps_data[ExifTags.GPS.GPSDestBearing] = round(gpx_point.heading,2)
        gps_data[ExifTags.GPS.GPSImgDirection] = round(gpx_point.heading,2) # todo riktig verdi

    # log(str(base_data) + " " + str(gps_data))
    exif = img.getexif()
    exif.update([*base_data.items(), (ExifTags.IFD.GPSInfo, gps_data)])
    return exif

def create_xmp_pano_data(img: Image.Image) -> bytes:
    w, h = img.size
    return str.encode(f"""<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Image::ExifTool 12.40'>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>

 <rdf:Description rdf:about=''
  xmlns:GPano='http://ns.google.com/photos/1.0/panorama/'>
  <GPano:CroppedAreaImageHeightPixels>{h}</GPano:CroppedAreaImageHeightPixels>
  <GPano:CroppedAreaImageWidthPixels>{w}</GPano:CroppedAreaImageWidthPixels>
  <GPano:CroppedAreaLeftPixels>0</GPano:CroppedAreaLeftPixels>
  <GPano:CroppedAreaTopPixels>0</GPano:CroppedAreaTopPixels>
  <GPano:FullPanoHeightPixels>{h}</GPano:FullPanoHeightPixels>
  <GPano:FullPanoWidthPixels>{w}</GPano:FullPanoWidthPixels>
  <GPano:ProjectionType>equirectangular</GPano:ProjectionType>
  <GPano:UsePanoramaViewer>True</GPano:UsePanoramaViewer>
 </rdf:Description>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>""")

if __name__ == '__main__':
    create_nadir(
        Path("./test_files/nadir_3k.png"),
        Path("./test_files/nadir_3k_out3.png"),
    )
    #
    # # from PIL import Image, ExifTags
    # # from matsemanns_streetview_tools.image import apply_image_pipeline
    # # img = Image.open("./test_files/test_output/GS012109-000001.jpg")
    # img = Image.open("./test_files/GS012814-000004.jpg")
    # nadir = Image.open("test_files/nadir_3k_out.png")
    #
    # img2 = apply_image_pipeline(img, nadir, 1.1, 1.05, 1.05, None)
    #
    # gpx_point = GpxPoint(
    #     lat=Decimal("60.051034"),
    #     lon=Decimal("10.688985"),
    #     ele=Decimal("367.2"),
    #     utc_time=datetime(2022, 8, 17, 13, 37, 55, 666),
    #     heading=Decimal("214.2")
    # )
    # exif = create_exif_data(img2, gpx_point)
    # xmp_data = create_xmp_pano_data(img)
    #
    # # exif.update([*base_data.items(), (ExifTags.IFD.GPSInfo, gps_data)])
    # print(exif)
    # # only writes xmp in pillow, not pillow-simd hmmm
    # img2.save("./test_files/test_output/test_pillow7_qual.jpg", quality=95, exif=exif, xmp=xmp_data)
