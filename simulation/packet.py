"""Packet model for the 5G URLLC healthcare simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Packet:
    """Represents one network packet with timing and outcome fields."""

    id: int
    packet_type: str  # "URLLC", "eMBB", or "IoT"
    size: int  # abstract units (affects transmission delay)
    arrival_time: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    dropped: bool = False
    drop_reason: Optional[str] = None

    @property
    def latency(self) -> Optional[float]:
        """End-to-end delay for successfully delivered packets."""
        if self.dropped or self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.arrival_time

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.packet_type,
            "size": self.size,
            "arrival_time": self.arrival_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "dropped": self.dropped,
            "drop_reason": self.drop_reason,
            "latency": self.latency,
        }


# SimPy PriorityResource: lower priority value = served first
PRIORITY_URLLC = 0
PRIORITY_EMBB = 5
PRIORITY_IOT = 10


def priority_for_type(packet_type: str) -> int:
    if packet_type == "URLLC":
        return PRIORITY_URLLC
    if packet_type == "eMBB":
        return PRIORITY_EMBB
    if packet_type == "IoT":
        return PRIORITY_IOT
    return 20
