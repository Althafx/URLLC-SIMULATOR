# URLLC Slice for Remote Healthcare (5G Network Simulation)

Academic **Python simulation** of a congested 5G-style transport link serving a **remote robotic surgery** story: a doctor in **Kerala** operates on a patient in **Delhi**. The model is **not** a real 5G implementation; it uses **SimPy** to show why **URLLC (Ultra-Reliable Low-Latency Communication)** style **priority** matters when video (**eMBB**) and **IoT** sensors compete for the same bottleneck.

## What the simulation does

- Generates three traffic types with a fixed random mix: **URLLC 20%**, **eMBB 50%**, **IoT 30%**.
- Sends packets through a **single-server queue** with a **finite buffer**.
- **Mode 1 — Normal network:** FIFO `Resource` (no class-based priority).
- **Mode 2 — URLLC slice:** `PriorityResource` so **URLLC** is served before **eMBB** and **IoT**.
- Applies **packet loss** when the **queue is full** and under **overload** (probabilistic when the queue is stressed).
- Reports **latency** (arrival → end of service), **loss rate**, and **reliability** (% delivered).

## Project layout

```
urllc-healthcare-simulation/
├── simulation/
│   ├── main.py              # run_scenario(...) entry point
│   ├── network.py           # SimPy queue + link
│   ├── packet.py            # Packet dataclass + priorities
│   ├── traffic_generator.py # arrivals + sizes
│   ├── scheduler.py         # priority mapping
│   ├── metrics.py           # aggregates
├── analysis/
│   ├── graphs.py            # matplotlib figures
├── app.py                   # Streamlit UI
├── requirements.txt
└── README.md
```

## Setup

1. Install **Python 3.10+** (3.11 recommended).
2. Create a virtual environment (optional but good practice):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## How to run

From the `urllc-healthcare-simulation` directory:

```bash
streamlit run app.py
```

**CLI smoke test** (prints summary JSON without the full packet list):

```bash
python -m simulation.main
```

## Using the dashboard

- **Simulation time** — longer runs produce smoother statistics.
- **Traffic load** — increase toward `1.0` to create **congestion** (queues build, latency grows, drops appear).
- **Compare Normal vs URLLC slice** — runs the **same random seed** twice so you can contrast **FIFO** vs **priority** fairly.
- Charts show **average latency**, **packet loss %**, and **reliability %** **per traffic class**.

## Example outcome (typical pattern)

With **high load** and a **tight queue**, you should see:

- **URLLC** packets with **lower average latency** when the slice is **enabled**.
- **eMBB / IoT** often wait longer when URLLC is prioritized (expected trade-off on a shared link).

Exact numbers depend on **seed**, **load**, and **queue size** — that is normal for event-driven simulations.

## Academic framing (viva / report)

- **URLLC** = strict latency and reliability targets for **control loops** (here: surgery commands).
- **Network slicing** = logical separation; here modeled only as **scheduler priority** + **overload behavior** on one hop.
- **Limitations:** one bottleneck, no radio channel, no TCP, no real 3GPP timers — scope stays **pedagogical**.

## License

Educational use. Adapt freely for coursework with attribution.
