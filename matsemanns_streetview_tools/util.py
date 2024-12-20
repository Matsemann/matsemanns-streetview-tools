from datetime import datetime, timezone
from os import environ
from pathlib import Path
from dotenv import load_dotenv


def _log_tqdm():
    from tqdm import tqdm

    def logger(str):
        tqdm.write(str)

    return logger


logger_impls = [_log_tqdm()]


def add_file_logger(file: Path):
    file.touch()
    file_handle = open(file, "a")

    def _file_logger(str):
        file_handle.write(str + "\n")
        file_handle.flush()

    global logger_impls
    logger_impls.append(_file_logger)


def log(str: str) -> None:
    for logger in logger_impls:
        logger(f"[{datetime.now()}] {str}")


def exif_date_to_datetime(exifdate: str) -> datetime:
    # On a weird format like "2023:08:17 15:06:25.299"
    # We assume utc
    iso_string = exifdate.replace(":", "-", 2)
    dt = datetime.fromisoformat(iso_string)
    dt = dt.replace(tzinfo=timezone.utc)
    return dt


def datetime_to_exifdatetime(dt: datetime) -> str:
    return dt.strftime("%Y:%m:%d %H:%M:%S")


def datetime_to_exifdate(dt: datetime) -> str:
    return dt.strftime("%Y:%m:%d")


# Paths to tools
load_dotenv()


def magick_path() -> str:
    return environ.get("MAGICK_PATH", "magick")


def ffmpeg_path() -> str:
    return environ.get("FFMPEG_PATH", "ffmpeg")


def ffprobe_path() -> str:
    return environ.get("FFPROBE_PATH", "ffprobe")


def exiftool_path() -> str:
    return environ.get("EXIFTOOL_PATH", "exiftool")
