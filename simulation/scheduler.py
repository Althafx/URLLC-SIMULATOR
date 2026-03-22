"""
Scheduling policy for the simulated link.

When URLLC slicing is enabled, lower numeric priority is served first
(SimPy PriorityResource convention). When disabled, the link uses a plain
FIFO resource so all traffic classes are treated equally.
"""

from __future__ import annotations

from simulation.packet import priority_for_type


def request_priority(packet_type: str, urllc_enabled: bool) -> int:
    """Return SimPy request priority; ignored when using a non-priority Resource."""
    if not urllc_enabled:
        return 0
    return priority_for_type(packet_type)
