from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class GpxPoint:
    lat: Decimal
    lon: Decimal
    ele: Decimal
    utc_time: datetime
    heading: Decimal | None = None

@dataclass
class GpxTrack:
    name: str
    utc_time: datetime
    points: list[GpxPoint]