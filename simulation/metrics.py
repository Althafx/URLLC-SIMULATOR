"""Aggregate latency, loss, and reliability metrics from packet outcomes."""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from simulation.packet import Packet

PACKET_TYPES = ("URLLC", "eMBB", "IoT")


def _latency_stats(latencies: List[float]) -> Dict[str, Optional[float]]:
    if not latencies:
        return {"avg": None, "min": None, "max": None}
    return {
        "avg": float(statistics.mean(latencies)),
        "min": float(min(latencies)),
        "max": float(max(latencies)),
    }


def metrics_for_subset(packets: List[Packet]) -> Dict[str, Any]:
    total = len(packets)
    dropped = [p for p in packets if p.dropped]
    delivered = [p for p in packets if not p.dropped]
    latencies = [p.latency for p in delivered if p.latency is not None]

    loss_rate = (len(dropped) / total) if total else 0.0
    reliability_pct = (len(delivered) / total * 100.0) if total else 0.0
    stats = _latency_stats(latencies)

    return {
        "total_packets": total,
        "dropped_packets": len(dropped),
        "delivered_packets": len(delivered),
        "packet_loss_rate": loss_rate,
        "reliability_pct": reliability_pct,
        "avg_latency": stats["avg"],
        "min_latency": stats["min"],
        "max_latency": stats["max"],
    }


def compute_metrics(packets: List[Packet], urllc_enabled: bool) -> Dict[str, Any]:
    """
    Structured summary for the UI and reports.

    Returns overall figures plus per-traffic-class breakdown.
    """
    overall = metrics_for_subset(packets)
    by_type: Dict[str, Dict[str, Any]] = {}
    for t in PACKET_TYPES:
        subset = [p for p in packets if p.packet_type == t]
        by_type[t] = metrics_for_subset(subset)

    return {
        "urllc_enabled": urllc_enabled,
        "overall": overall,
        "by_type": by_type,
        "packets": [p.to_dict() for p in packets],
    }
