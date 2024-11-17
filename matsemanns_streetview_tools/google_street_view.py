import json
import os
import time
from datetime import timedelta
from pathlib import Path

import requests
from google.auth.credentials import TokenState
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from base64 import urlsafe_b64decode

from pydantic import BaseModel
from requests import Session
from tqdm import tqdm

from matsemanns_streetview_tools import metadata
from matsemanns_streetview_tools.gpx import GpxTrack
from matsemanns_streetview_tools.util import log

# No way to avoid publishing this for a public desktop client, even the hidden value.
# Using PKCE, but google requires the value to be used when requesting the token
# Key is scoped to have access to nothing but street view publish anyways, and it's still
# uploaded on user's behalf so not ripe for abuse
config_str = b"eyJpbnN0YWxsZWQiOiB7ImNsaWVudF9pZCI6ICI0NzI4NDIxODc0NDUtZ2hwZGg5bHN2YnAybGtwZGZrcjczZmlsYzQwYWNpNmEuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCAicHJvamVjdF9pZCI6ICJtYXRzZW1hbm5zLXN0cmVldHZpZXctdG9vbHMiLCAiYXV0aF91cmkiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLCAidG9rZW5fdXJpIjogImh0dHBzOi8vb2F1dGgyLmdvb2dsZWFwaXMuY29tL3Rva2VuIiwgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLCAiY2xpZW50X3NlY3JldCI6ICJHT0NTUFgtSEVCTmxOZm5TTDZTcjgzbDg2OXhmWDJZYmpoQiIsICJyZWRpcmVjdF91cmlzIjogWyJodHRwOi8vbG9jYWxob3N0Il19fQ=="
config = json.loads(urlsafe_b64decode(config_str))

user_cred_file = Path("./google_credentials.json")


def _get_user_credentials() -> Credentials:
    if not user_cred_file.exists():
        raise RuntimeError("No google auth configured, run 'google auth'")
    return Credentials.from_authorized_user_file(str(user_cred_file.resolve()))


def _save_credentials(creds: Credentials) -> None:
    user_cred_file.write_text(creds.to_json())


def _get_credentials_token(creds: Credentials) -> str:
    if creds.token_state in [TokenState.STALE, TokenState.INVALID]:
        log("refreshing google token")
        creds.refresh(Request())
        _save_credentials(creds)

    return creds.token


def _get_header_token(creds: Credentials) -> str:
    return f"Bearer {_get_credentials_token(creds)}"


def authorize():
    """
    Uses the InstalledAppFlow to give us a token we later can use for the street view api
    """
    flow = InstalledAppFlow.from_client_config(
        client_config=config,
        scopes=["https://www.googleapis.com/auth/streetviewpublish"],
    )

    log("Starting auth flow, open the following URL in the browser (if it didn't open automatically) and follow the steps.")  # fmt: skip
    log("This will generate a 'token' that this app later can use to communicate with Street View on your behalf (like uploading videos). ")  # fmt: skip
    log("When approving in your browser, you give this token access only to do this, nothing else.")  # fmt: skip
    log("Additionally, the token is only ever stored on this computer, so you can delete it and revoke access at any time.")  # fmt: skip
    log("Open the link, or press CTRL+C to abort")

    credentials: Credentials = flow.run_local_server()  # type: ignore

    _save_credentials(credentials)

    log(f"Token stored in {user_cred_file}")


def upload_streetview_video(
    video: Path,
    gpx_track: GpxTrack,
    chunk_size_mib: int = 16,
) -> None:
    """Uses the Google Street View Publish API to upload a video together with gps data.
    Uploads the video in chunks, so even large files are handled. Also supports interruptions and can resume.

    https://developers.google.com/streetview/publish/reference/rest

    """
    credentials = _get_user_credentials()

    # Sanity check the metadata, the gpx should cover the video
    _verify_valid_gpx_for_video(video, gpx_track)
    gps_points = _create_google_gps_data_from_gpx(gpx_track)

    # We don't use default headers in the session, instead make sure we have an up-to-date token each request, as this
    # upload process can last for a long time for large files, making it expire between requests
    session = requests.Session()

    # Tell google we want to upload something, get a ref back
    log("Step 1/3: Preparing for upload")
    upload_url = _get_upload_url(session, credentials)

    # Upload the file to the reference we got, parts at a time
    log(f"Step 2/3: Uploading video to {upload_url}")
    _chunk_upload_video(session, credentials, video, upload_url, chunk_size_mib)

    # Tell google this should be a streetview together with the gps data
    log("Step 3/3: Attaching gps data to the uploaded video and publishing")
    _create_street_view_photosequence(session, credentials, gps_points, upload_url)

    log(f"Successfully uploaded {video}")


def _get_upload_url(session: Session, credentials: Credentials) -> str:
    try:
        res = session.post(
            "https://streetviewpublish.googleapis.com/v1/photoSequence:startUpload",
            headers={"Authorization": _get_header_token(credentials)},
            timeout=60,
        )
        res.raise_for_status()

        return res.json()["uploadUrl"]
    except Exception as err:
        log(f"ERROR: Something went wrong, {err}")
        log(
            "If the error is 401 or 403, check if the token is valid or authorize again"
        )
        raise err


def _chunk_upload_video(
    session: Session,
    credentials: Credentials,
    video: Path,
    upload_url: str,
    chunk_size_mib: int,
) -> None:
    total_bytes = os.path.getsize(video)

    # Tell google we want to do it in chunks / resumable
    # Based on https://developers.google.com/streetview/publish/resumable-uploads
    res = session.post(
        upload_url,
        headers={
            "Authorization": _get_header_token(credentials),
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Header-Content-Length": str(total_bytes),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "X-Goog-Upload-Command": "start",
        },
    )
    res.raise_for_status()
    resumable_url = res.headers["X-Goog-Upload-URL"]

    uploaded_bytes = 0
    chunk_size = 1024 * 1024 * chunk_size_mib

    with open(video, "rb") as file:
        with tqdm(
            total=total_bytes, unit="B", leave=True, unit_scale=True, unit_divisor=1024
        ) as pbar:
            while uploaded_bytes < total_bytes:
                chunk = file.read(chunk_size)

                # If it's the last chunk to upload, different header command
                remaining = total_bytes - uploaded_bytes
                command = "upload, finalize" if remaining <= chunk_size else "upload"

                try:
                    session.post(
                        resumable_url,
                        data=chunk,
                        headers={
                            "Authorization": _get_header_token(credentials),
                            "X-Goog-Upload-Offset": str(uploaded_bytes),
                            "X-Goog-Upload-Command": command,
                            "Content-Length": str(len(chunk)),
                        },
                        timeout=60,
                    )

                    uploaded_bytes += len(chunk)
                    pbar.update(len(chunk))
                    # log(f"Uploaded {uploaded_bytes / 1024 / 1024} MiB")
                except Exception as err:
                    log(
                        f"Something went wrong uploading a chunk {err}, will try to resume"
                    )

                    uploaded_bytes = _resume_upload(credentials, resumable_url, session)
                    file.seek(uploaded_bytes)  # Seek to where we should resume from
                    log(f"Success, resuming upload from byte {uploaded_bytes}")


def _resume_upload(credentials, resumable_url, session) -> int:
    for attempt in range(10):
        if attempt < 3:
            time.sleep(5)
        else:
            time.sleep(30)
        try:
            res = session.post(
                resumable_url,
                headers={
                    "Authorization": _get_header_token(credentials),
                    "X-Goog-Upload-Command": "query",
                },
                timeout=30,
            )
            res.raise_for_status()
        except Exception as err2:
            log(f"Didn't work, trying again {err2}")
            continue

        status = res.headers["X-Goog-Upload-Status"]

        if status != "active":
            log("Upload is no longer active, aborting")
            raise RuntimeError("Upload no longer active")

        return int(res.headers["X-Goog-Upload-Size-Received"])

    log("No more attempts, aborting")
    raise RuntimeError("Out of attempts to resume the upload")


def _verify_valid_gpx_for_video(video: Path, gpx_track: GpxTrack) -> None:
    video_metadata = metadata.get_ffprobe_metadata(video)
    video_start = video_metadata.get_creation_time()
    video_end = video_start + video_metadata.get_duration()

    gpx_start = gpx_track.points[0].utc_time
    gpx_end = gpx_track.points[-1].utc_time
    # A small delta to handle that video time is in whole seconds
    if gpx_start > video_start + timedelta(seconds=1):
        raise RuntimeError(
            f"Gpx file starts at {gpx_start}, which is after video starts ({video_start})"
        )
    if video_end > gpx_end + timedelta(seconds=1):
        raise RuntimeError(
            f"Gpx file ends at {gpx_end}, which is before video ends ({video_end})"
        )


class UploadReference(BaseModel):
    uploadUrl: str


class LatLng(BaseModel):
    latitude: float
    longitude: float


class Pose(BaseModel):
    latLngPair: LatLng
    altitude: float | None
    gpsRecordTimestampUnixEpoch: str
    heading: float | None = None
    pitch: float | None = None
    roll: float | None = None


class PhotoSequenceRequest(BaseModel):
    uploadReference: UploadReference
    rawGpsTimeline: list[Pose]
    gpsSource: str


def _create_google_gps_data_from_gpx(gpx_track: GpxTrack) -> list[Pose]:
    gps_data = []

    for point in gpx_track.points:
        gps_data.append(
            Pose(
                latLngPair=LatLng(
                    latitude=float(point.lat),
                    longitude=float(point.lon),
                ),
                altitude=float(point.ele),
                gpsRecordTimestampUnixEpoch=point.utc_time.strftime(
                    # "%Y-%m-%dT%H:%M:%S.%fZ" # TODO reactivate
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                heading=float(point.heading) if point.heading is not None else None,
                # TODO heading is not parsed from gpx file at the moment
            )
        )

    return gps_data


def _create_street_view_photosequence(
    session: Session,
    credentials: Credentials,
    gps_data: list[Pose],
    upload_url: str,
) -> None:
    sequence_request = PhotoSequenceRequest(
        uploadReference=UploadReference(uploadUrl=upload_url),
        rawGpsTimeline=gps_data,
        gpsSource="PHOTO_SEQUENCE",
    )
    res = session.post(
        "https://streetviewpublish.googleapis.com/v1/photoSequence",
        data=sequence_request.model_dump_json(),
        headers={"Authorization": _get_header_token(credentials)},
        params={"inputType": "VIDEO"},
        timeout=60,
    )
    res.raise_for_status()
    sequence_id = res.json()["name"]
    log(f"Completed, saved as {sequence_id}")
