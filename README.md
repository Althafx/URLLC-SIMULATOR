# URLLC Healthcare Simulation

A **simple, educational** simulation of a **busy 5G-style link** shared by three traffic types:

| Type   | Idea in this project        |
|--------|-----------------------------|
| **URLLC** | Time-critical control (e.g. surgery commands) |
| **eMBB**  | Heavy traffic (e.g. video) |
| **IoT**   | Sensors / telemetry        |

**What you learn:** when the link is crowded, **who gets served first** changes **latency**, **packet loss**, **reliability**, and **jitter**. Turning on a **URLLC-style priority slice** helps critical traffic — often at the cost of lower-priority traffic on the **same** link.

> This is **not** a real 5G or radio simulator. It is a **queue + scheduler** model built with **SimPy**, shown in a **Streamlit** app.

---

## Run the app (quick)

1. **Python 3.10+** installed.

2. Open a terminal in this folder (`urllc-sim`).

3. (Recommended) Virtual environment:

   **Windows**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

   **macOS / Linux**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

4. Your browser opens (usually **http://localhost:8501**).

**No Streamlit?** After `pip install -r requirements.txt`, the command above should work.

---

## What you do in the app

1. **Landing** — Enter the simulation.
2. **Wizard** — Set:
   - simulation duration  
   - traffic load  
   - **traffic intensity** (low / medium / high, with bursts on **high**)  
   - queue size  
3. **SIMULATE** — The app runs the models and opens **Results**.
4. **Results** — Charts, tables, optional Kerala → Delhi animation, toggles for **URLLC** views.

**← New simulation** goes back to the landing page.

---

## What the simulation actually does

- **Traffic mix:** about **20% URLLC**, **50% eMBB**, **30% IoT** (random per packet).
- **One bottleneck:** single server, **finite queue**, drops when full or under congestion.
- **Two scheduling modes** (same random seed for a fair comparison):
  - **Normal:** first-come-first-served (`simpy.Resource`).
  - **URLLC slice on:** priority order **URLLC → eMBB → IoT** (`simpy.PriorityResource`).
- **Heavy traffic:** higher intensity + optional **burst** arrivals; **normal vs heavy** is also compared in one chart.
- **Metrics:** latency is in **simulation time units** (not real milliseconds), plus loss, reliability (% delivered), and **jitter** (variation in latency).

---

## Project folders (where to look)

```
urllc-sim/
├── app.py                 # Streamlit UI (landing → wizard → results)
├── simulation/
│   ├── main.py            # run_scenario(...) — entry for one run
│   ├── network.py         # SimPy queue + link + drops
│   ├── packet.py          # Packet + priority numbers
│   ├── traffic_generator.py
│   ├── scheduler.py
│   └── metrics.py         # latency, loss, reliability, jitter
├── analysis/
│   └── graphs.py          # Plotly charts
├── requirements.txt
├── README.md              # this file
└── MSC_CLASSROOM_GUIDE.md # teaching / presentation notes (optional)
```

---

## Run without the browser (quick check)

Prints a **short JSON summary** (no full packet dump):

```bash
python -m simulation.main
```

(Run from inside `urllc-sim` with dependencies installed.)

---

## Tech stack

- **Python**
- **Streamlit** — UI
- **SimPy** — discrete-event simulation
- **Plotly** — charts

---

-
