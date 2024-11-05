FROM ubuntu:22.04
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/

# Install exiftool and ffmpeg, git needed to download an uv dep
RUN apt-get update -y && apt-get install -y exiftool ffmpeg git

# Need a newer version of magick (7), but it comes as an appimage and we don't have
# fuse working inside docker, so just add extract and run env
ADD https://imagemagick.org/archive/binaries/magick /bin/magick
RUN chmod +x /bin/magick
ENV APPIMAGE_EXTRACT_AND_RUN=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.4.29 /uv /bin/uv

WORKDIR /app
# install dependencies
COPY pyproject.toml uv.lock /app/
RUN uv sync

# copy in the code
COPY matsemanns_streetview_tools/ /app/matsemanns_streetview_tools
COPY cli.py /app/


ENTRYPOINT ["echo", "run with 'uv run cli.py <command>'"]

