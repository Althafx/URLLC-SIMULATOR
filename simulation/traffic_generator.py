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

INTENSITY_FACTORS = {
    "low": 1.25,
    "medium": 1.00,
    "high": 0.62,
}


def inter_arrival_time(load: float, rng: random.Random) -> float:
    """
    Higher load → shorter gaps → more congestion.
    At load=0.5 the link is near saturation; at 0.8+ it's clearly overloaded.
    """
    load = max(0.1, min(1.0, load))
    mean_gap = 0.18 - 0.14 * load  # range: 0.166 (light) → 0.04 (max)
    return rng.expovariate(1.0 / mean_gap)


def inter_arrival_time_profiled(
    load: float,
    rng: random.Random,
    *,
    traffic_intensity: str = "medium",
    burst_active: bool = False,
) -> float:
    """
    Inter-arrival with scenario profile and optional burst pressure.

    - traffic_intensity controls baseline congestion pressure.
    - burst_active shrinks the mean gap further for short spikes.
    """
    load = max(0.1, min(1.0, load))
    base_gap = 0.18 - 0.14 * load
    factor = INTENSITY_FACTORS.get(traffic_intensity, 1.0)
    mean_gap = base_gap * factor
    if burst_active:
        mean_gap *= 0.45
    mean_gap = max(0.012, mean_gap)
    return rng.expovariate(1.0 / mean_gap)


def packet_stream(
    env_time_start: float,
    sim_duration: float,
    load: float,
    traffic_intensity: str = "medium",
    burst_enabled: bool = False,
    seed: int | None = None,
) -> Iterator[Tuple[float, Packet]]:
    rng = random.Random(seed)
    t = float(env_time_start)
    pid = 0
    burst_period = 8.0
    burst_duration = 1.5
    while t < sim_duration:
        ptype = rng.choices(TYPES, weights=PROBS, k=1)[0]
        low, high = SIZE_RANGES[ptype]
        size = rng.randint(low, high)
        yield t, Packet(id=pid, packet_type=ptype, size=size, arrival_time=t)
        pid += 1
        in_burst = burst_enabled and ((t % burst_period) < burst_duration)
        t += inter_arrival_time_profiled(
            load,
            rng,
            traffic_intensity=traffic_intensity,
            burst_active=in_burst,
        )
