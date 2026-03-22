"""Random traffic generation with URLLC / eMBB / IoT mix."""

from __future__ import annotations

import random
from typing import Iterator, Tuple

from simulation.packet import Packet

# URLLC 20%, eMBB 50%, IoT 30%
TYPES = ["URLLC", "eMBB", "IoT"]
PROBS = [0.20, 0.50, 0.30]

# Size ranges (abstract units)
SIZE_RANGES = {
    "URLLC": (1, 3),    # surgical control — tiny
    "eMBB": (8, 16),    # video — large
    "IoT": (2, 6),      # sensor — medium
}


def inter_arrival_time(load: float, rng: random.Random) -> float:
    """
    Higher load → shorter gaps → more congestion.
    At load=0.5 the link is near saturation; at 0.8+ it's clearly overloaded.
    """
    load = max(0.1, min(1.0, load))
    mean_gap = 0.18 - 0.14 * load  # range: 0.166 (light) → 0.04 (max)
    return rng.expovariate(1.0 / mean_gap)


def packet_stream(
    env_time_start: float,
    sim_duration: float,
    load: float,
    seed: int | None = None,
) -> Iterator[Tuple[float, Packet]]:
    rng = random.Random(seed)
    t = 0.0
    pid = 0
    while t < sim_duration:
        ptype = rng.choices(TYPES, weights=PROBS, k=1)[0]
        low, high = SIZE_RANGES[ptype]
        size = rng.randint(low, high)
        yield t, Packet(id=pid, packet_type=ptype, size=size, arrival_time=t)
        pid += 1
        t += inter_arrival_time(load, rng)
