from datetime import datetime
from decimal import Decimal

from matsemanns_streetview_tools.gpx import GpxPoint


def gpx_point(
        lat: Decimal = Decimal(0),
        lon: Decimal = Decimal(0),
        ele: Decimal = Decimal(1000),
        utc_time: datetime | None = None ,
              ) -> GpxPoint:
    """Testutil for generating a valid gpxpoint
    where we for the test only care about some
    of the values and the rest can be arbitrary"""

    if not utc_time:
        utc_time = datetime.now()

    return GpxPoint(lat, lon, ele, utc_time)
