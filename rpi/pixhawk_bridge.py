import math
import logging
import time
from dataclasses import dataclass
from typing import Optional

from pymavlink import mavutil

log = logging.getLogger(__name__)


@dataclass
class GPSFix:
    lat: float
    lon: float
    alt_rel: float
    heading: float
    groundspeed: float
    timestamp: float


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class PixhawkBridge:
    def __init__(self, connection_string, baud=57600):
        self._conn_str = connection_string
        self._baud = baud
        self._mav = None

    def connect(self):
        log.info("Connecting to Pixhawk on %s @ %d baud ...", self._conn_str, self._baud)
        self._mav = mavutil.mavlink_connection(self._conn_str, baud=self._baud)
        self._mav.wait_heartbeat(timeout=30)
        log.info("Connected — heartbeat received (sysid=%d)", self._mav.target_system)
        self._mav.mav.request_data_stream_send(
            self._mav.target_system,
            self._mav.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            4, 1
        )

    def disconnect(self):
        if self._mav:
            self._mav.close()
            self._mav = None

    def get_gps(self) -> Optional[GPSFix]:
        if self._mav is None:
            raise RuntimeError("Not connected")
        msg = self._mav.recv_match(type=["GLOBAL_POSITION_INT"], blocking=True, timeout=2.0)
        if msg is None:
            return None
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        if lat == 0.0 and lon == 0.0:
            return None
        alt_rel = msg.relative_alt / 1000.0
        heading = msg.hdg / 100.0 if msg.hdg != 65535 else 0.0
        groundspeed = math.sqrt(msg.vx ** 2 + msg.vy ** 2) / 100.0
        return GPSFix(
            lat=lat, lon=lon, alt_rel=alt_rel,
            heading=heading, groundspeed=groundspeed,
            timestamp=time.time(),
        )

    def gps_fix_type(self) -> int:
        msg = self._mav.recv_match(type=["GPS_RAW_INT"], blocking=True, timeout=2.0)
        return msg.fix_type if msg else 0

    def wait_for_gps(self, min_fix_type=3, timeout=60.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.gps_fix_type() >= min_fix_type:
                return
            time.sleep(1.0)
        raise TimeoutError("No GPS fix")

    def has_arrived(self, target_lat, target_lon, radius_m) -> bool:
        fix = self.get_gps()
        if fix is None:
            return False
        return haversine_distance(fix.lat, fix.lon, target_lat, target_lon) <= radius_m
