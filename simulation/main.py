"""
Entry point to run one simulation scenario and return structured results.

Use this from Streamlit or scripts: `run_scenario(...)`.
"""

from __future__ import annotations

from typing import Any, Dict

from simulation.metrics import compute_metrics
from simulation.network import run_network_simulation


def run_scenario(
    sim_time: float,
    traffic_load: float,
    urllc_enabled: bool,
    max_queue: int = 12,
    seed: int | None = 42,
) -> Dict[str, Any]:
    """
    Execute the network simulation and attach computed metrics.

    Parameters
    ----------
    sim_time : float
        Simulation horizon (abstract time units).
    traffic_load : float
        0.1–1.0; higher values produce more arrivals (busier network).
    urllc_enabled : bool
        If True, URLLC slice uses priority scheduling on the bottleneck link.
    max_queue : int
        Maximum waiting packets before additional arrivals are dropped.
    seed : int, optional
        Reproducible randomness for traffic and service jitter.
    """
    packets = run_network_simulation(
        sim_time=sim_time,
        traffic_load=traffic_load,
        urllc_enabled=urllc_enabled,
        max_queue=max_queue,
        seed=seed,
    )
    return compute_metrics(packets, urllc_enabled=urllc_enabled)


if __name__ == "__main__":
    import json

    demo = run_scenario(sim_time=30.0, traffic_load=0.75, urllc_enabled=True)
    # Compact print without full packet list
    slim = {k: v for k, v in demo.items() if k != "packets"}
    print(json.dumps(slim, indent=2, default=str))
