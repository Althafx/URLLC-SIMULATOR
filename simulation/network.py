"""
Queue-based bottleneck link simulation using SimPy.

One constrained hop with finite buffer, overload drops, and optional
URLLC priority scheduling.
"""

from __future__ import annotations

import random
from typing import List

import simpy

from simulation.packet import Packet
from simulation.scheduler import request_priority
from simulation.traffic_generator import packet_stream


def _service_time(packet: Packet, rng: random.Random) -> float:
    """Transmission delay proportional to packet size."""
    base = 0.03
    per_unit = 0.012
    jitter = rng.uniform(0, 0.008)
    return base + packet.size * per_unit + jitter


def _should_drop(
    packet: Packet,
    load: float,
    occupancy: float,
    urllc_enabled: bool,
    rng: random.Random,
) -> bool:
    """
    Probabilistic congestion drop when queue occupancy is high.
    URLLC packets are protected when slicing is on.
    """
    if occupancy < 0.5:
        return False
    base_p = 0.20 * load * occupancy
    if urllc_enabled and packet.packet_type == "URLLC":
        base_p *= 0.05  # almost never dropped
    elif not urllc_enabled and packet.packet_type == "URLLC":
        base_p *= 1.3   # treated same as everything else
    return rng.random() < base_p


def run_network_simulation(
    sim_time: float,
    traffic_load: float,
    urllc_enabled: bool,
    max_queue: int = 8,
    seed: int | None = 42,
) -> List[Packet]:
    rng = random.Random((seed or 0) + 1)
    env = simpy.Environment()

    if urllc_enabled:
        link = simpy.PriorityResource(env, capacity=1)
    else:
        link = simpy.Resource(env, capacity=1)

    results: List[Packet] = []

    def handle_packet(pkt: Packet):
        waiting = len(link.queue)
        occupancy = (waiting + link.count) / max(1, max_queue)

        # Queue-full → drop (URLLC gets a reserved slot when slicing is on)
        if waiting >= max_queue:
            if urllc_enabled and pkt.packet_type == "URLLC":
                pass  # reserved slot — not dropped
            else:
                pkt.dropped = True
                pkt.drop_reason = "queue_full"
                results.append(pkt)
                return

        # Congestion drop
        if _should_drop(pkt, traffic_load, occupancy, urllc_enabled, rng):
            pkt.dropped = True
            pkt.drop_reason = "congestion"
            results.append(pkt)
            return

        # Serve
        if urllc_enabled:
            prio = request_priority(pkt.packet_type, True)
            with link.request(priority=prio) as req:
                yield req
                pkt.start_time = env.now
                yield env.timeout(_service_time(pkt, rng))
                pkt.end_time = env.now
        else:
            with link.request() as req:
                yield req
                pkt.start_time = env.now
                yield env.timeout(_service_time(pkt, rng))
                pkt.end_time = env.now

        results.append(pkt)

    stream_seed = seed if seed is not None else 0
    for arrival_t, pkt in packet_stream(0.0, sim_time, traffic_load, seed=stream_seed):
        def arrival_process(t: float = arrival_t, p: Packet = pkt):
            yield env.timeout(max(0.0, t - env.now))
            env.process(handle_packet(p))
        env.process(arrival_process())

    env.run(until=sim_time)
    results.sort(key=lambda p: p.id)
    return results
