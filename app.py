"""
URLLC Healthcare Simulation — stepped presenter flow + results dashboard.

Run:  python -m streamlit run app.py
"""

from __future__ import annotations

import time

import streamlit as st

from analysis.graphs import (
    comparison_table,
    mode_labels,
    plotly_chart_config,
    plotly_grouped_bar,
)
from simulation.main import run_scenario

DEFAULT_SEED = 42

# Latency values are SimPy simulation time (abstract units), not wall-clock ms.
LATENCY_UNIT = "sim units"


def _fmt_latency(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f} {LATENCY_UNIT}"


def _fmt_loss_pct(rate: float) -> str:
    return f"{rate * 100.0:.1f}%"


def _fmt_reliability_pct(pct: float) -> str:
    return f"{pct:.0f}%"


def _traffic_class_matrix_html(enable_urllc: bool, res_normal: dict, res_urllc: dict) -> str:
    """Large HTML table: per-class metrics with plain-language roles."""
    roles = {
        "URLLC": "Surgical & robotic control",
        "eMBB": "Video & high throughput",
        "IoT": "Sensors & telemetry",
    }
    rows_html = []
    for t in ("URLLC", "eMBB", "IoT"):
        bn = res_normal["by_type"][t]
        role = roles[t]
        tag = f'<span class="tc-tag tc-tag--{t.lower()}">{t}</span>'
        if enable_urllc:
            bu = res_urllc["by_type"][t]
            ln = bn.get("avg_latency")
            lu = bu.get("avg_latency")
            rows_html.append(
                f"<tr><td>{tag}</td><td class=\"tc-role\">{role}</td>"
                f"<td class=\"tc-num\">{_fmt_latency(ln)}</td>"
                f"<td class=\"tc-num tc-num--accent\">{_fmt_latency(lu)}</td>"
                f"<td class=\"tc-num\">{_fmt_loss_pct(bn['packet_loss_rate'])}</td>"
                f"<td class=\"tc-num tc-num--accent\">{_fmt_loss_pct(bu['packet_loss_rate'])}</td>"
                f"<td class=\"tc-num\">{_fmt_reliability_pct(bn['reliability_pct'])}</td>"
                f"<td class=\"tc-num tc-num--accent\">{_fmt_reliability_pct(bu['reliability_pct'])}</td></tr>"
            )
        else:
            ln = bn.get("avg_latency")
            rows_html.append(
                f"<tr><td>{tag}</td><td class=\"tc-role\">{role}</td>"
                f"<td class=\"tc-num\">{_fmt_latency(ln)}</td>"
                f"<td class=\"tc-num\">{_fmt_loss_pct(bn['packet_loss_rate'])}</td>"
                f"<td class=\"tc-num\">{_fmt_reliability_pct(bn['reliability_pct'])}</td></tr>"
            )

    if enable_urllc:
        thead = (
            "<thead><tr>"
            "<th>Class</th><th>Role</th>"
            "<th>Latency<br/><span class=\"tc-thsub\">sim units · no slice</span></th>"
            "<th class=\"tc-th--accent\">Latency<br/><span class=\"tc-thsub\">sim units · URLLC on</span></th>"
            "<th>Packet loss<br/><span class=\"tc-thsub\">no slice</span></th>"
            "<th class=\"tc-th--accent\">Packet loss<br/><span class=\"tc-thsub\">URLLC on</span></th>"
            "<th>Delivered<br/><span class=\"tc-thsub\">no slice</span></th>"
            "<th class=\"tc-th--accent\">Delivered<br/><span class=\"tc-thsub\">URLLC on</span></th>"
            "</tr></thead>"
        )
    else:
        thead = (
            "<thead><tr>"
            "<th>Class</th><th>Role</th>"
            "<th>Avg latency<br/><span class=\"tc-thsub\">sim units</span></th>"
            "<th>Packet loss</th>"
            "<th>Packets delivered</th>"
            "</tr></thead>"
        )

    return (
        '<div class="tc-wrap">'
        '<table class="traffic-matrix">'
        f"{thead}<tbody>{''.join(rows_html)}</tbody></table>"
        '<p class="tc-foot">Average latency = mean delay for successfully delivered packets. '
        f"Latency uses the model&rsquo;s <b>simulation time axis</b> ({LATENCY_UNIT}), the same unit as service and wait times in SimPy &mdash; "
        "not wall-clock milliseconds. Loss and delivery are % of all packets in that class.</p>"
        "</div>"
    )


# ── Session defaults ──
if "phase" not in st.session_state:
    st.session_state.phase = "landing"  # landing | wizard | boot | results
if "wiz_step" not in st.session_state:
    st.session_state.wiz_step = 0
if "wiz_dur" not in st.session_state:
    st.session_state.wiz_dur = 50
if "wiz_load" not in st.session_state:
    st.session_state.wiz_load = 0.6
if "wiz_queue" not in st.session_state:
    st.session_state.wiz_queue = 8

st.set_page_config(
    page_title="URLLC 5G Simulation",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _reset_wizard() -> None:
    """Clear results and return to the landing page (full intro flow)."""
    st.session_state.phase = "landing"
    st.session_state.wiz_step = 0
    for k in ("res_normal", "res_urllc"):
        st.session_state.pop(k, None)


def _demo_assets():
    """Return (css, panel_norm_html, panel_urllc_html) for SVG link demo."""
    css = """
<style>
.surgery-dual-wrap { max-width: 980px; margin: 0 auto 1.25rem auto; font-family: system-ui, sans-serif; }
.surgery-dual-row { display: flex; flex-wrap: wrap; gap: 14px; justify-content: center; align-items: stretch; }
.surgery-panel {
  flex: 1 1 300px; max-width: 480px;
  border-radius: 12px;
  background: linear-gradient(180deg, #0f1419 0%, #0a0d12 100%);
  border: 1px solid #1e293b;
  padding: 10px 12px 6px 12px;
  box-sizing: border-box;
}
.surgery-panel--solo { max-width: 520px; margin-left: auto; margin-right: auto; }
.surgery-panel svg { display: block; width: 100%; height: auto; max-height: 210px; }
.panel-badge {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; padding: 4px 10px; border-radius: 6px; margin-bottom: 6px;
}
.panel-badge--norm { background: #292524; color: #a8a29e; border: 1px solid #44403c; }
.panel-badge--urllc { background: #0c4a6e; color: #7dd3fc; border: 1px solid #0369a1; }
@keyframes beamPulseCyan {
  0%, 100% { stroke-opacity: 0.45; stroke-width: 2; }
  50%      { stroke-opacity: 1; stroke-width: 3.5; }
}
@keyframes beamPulseDim {
  0%, 100% { stroke-opacity: 0.2; stroke-width: 1.5; }
  50%      { stroke-opacity: 0.55; stroke-width: 2.2; }
}
.beam-norm { stroke: #78716c; fill: none; stroke-dasharray: 6 10; animation: beamPulseDim 3s ease-in-out infinite; }
.beam-urllc { stroke: #22d3ee; fill: none; stroke-dasharray: 8 5; animation: beamPulseCyan 1.8s ease-in-out infinite; }
.pkt-norm { fill: #f59e0b; filter: drop-shadow(0 0 4px #b45309); }
.pkt-urllc { fill: #f472b6; filter: drop-shadow(0 0 8px #ec4899); }
.demo-lbl { fill: #94a3b8; font-size: 10px; }
.demo-h { fill: #e2e8f0; font-size: 12px; font-weight: 600; }
.demo-foot { fill: #64748b; font-size: 9px; }
.demo-lat { font-family: system-ui, sans-serif; font-size: 14px; font-weight: 800; letter-spacing: 0.04em; }
.demo-lat--norm { fill: #fbbf24; filter: drop-shadow(0 0 8px rgba(251,191,36,0.45)); }
.demo-lat--urllc { fill: #22d3ee; filter: drop-shadow(0 0 10px rgba(34,211,238,0.55)); }
.demo-lat-sub { fill: #64748b; font-size: 8px; font-weight: 600; letter-spacing: 0.12em; }
</style>
"""
    pnorm = """
  <div class="surgery-panel SURGEON_SOLO_CLASS">
    <span class="panel-badge panel-badge--norm">Without URLLC</span>
    <svg viewBox="0 0 440 188" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gNormAnimR" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" style="stop-color:#44403c;stop-opacity:0.35"/>
          <stop offset="100%" style="stop-color:#57534e;stop-opacity:0.2"/>
        </linearGradient>
      </defs>
      <rect width="440" height="188" fill="url(#gNormAnimR)" rx="8"/>
      <text x="220" y="22" text-anchor="middle" class="demo-h">Normal network (FIFO)</text>
      <text x="220" y="38" text-anchor="middle" class="demo-foot">Surgery commands wait with video &amp; sensor data</text>
      <!-- Surgeon: simple person + computer -->
      <rect x="18" y="52" width="78" height="58" rx="6" fill="#111827" stroke="#44403c"/>
      <g transform="translate(18,52)">
        <circle cx="22" cy="17" r="8" fill="#57534e" stroke="#78716c" stroke-width="1.2"/>
        <path d="M 10 28 Q 22 22 34 28 L 32 48 L 12 48 Z" fill="#44403c" stroke="#57534e" stroke-width="1"/>
        <rect x="36" y="9" width="34" height="28" rx="2" fill="#292524" stroke="#57534e" stroke-width="1"/>
        <rect x="39" y="12" width="28" height="19" rx="1" fill="#0c0a09" stroke="#44403c"/>
        <rect x="48" y="37" width="10" height="5" rx="1" fill="#292524" stroke="#44403c"/>
        <rect x="42" y="42" width="22" height="3" rx="1" fill="#292524" stroke="#44403c"/>
      </g>
      <text x="57" y="124" text-anchor="middle" class="demo-lbl">Surgeon</text>
      <!-- Surgical robot arm -->
      <rect x="344" y="52" width="78" height="58" rx="6" fill="#111827" stroke="#44403c"/>
      <g transform="translate(344,52)">
        <ellipse cx="56" cy="51" rx="15" ry="3.8" fill="#292524" stroke="#44403c"/>
        <rect x="50" y="30" width="12" height="22" rx="2" fill="#36302a" stroke="#57534e"/>
        <circle cx="56" cy="30" r="4" fill="#44403c" stroke="#57534e"/>
        <path d="M 56 30 L 38 20" stroke="#78716c" stroke-width="3.2" stroke-linecap="round"/>
        <circle cx="38" cy="20" r="3.2" fill="#57534e"/>
        <path d="M 38 20 L 16 28" stroke="#78716c" stroke-width="2.6" stroke-linecap="round"/>
        <circle cx="16" cy="28" r="2.8" fill="#57534e"/>
        <path d="M 10 24 L 6 28 L 10 32 M 14 24 L 10 28 L 14 32" fill="none" stroke="#a8a29e" stroke-width="1.6" stroke-linecap="round"/>
        <circle cx="8" cy="28" r="3.5" fill="none" stroke="#57534e" stroke-width="1"/>
      </g>
      <text x="383" y="124" text-anchor="middle" class="demo-lbl">Robot</text>
      <path class="beam-norm" d="M 96 88 C 180 42, 260 42, 344 88"/>
      <text x="220" y="72" text-anchor="middle" class="demo-lat-sub">CONTROL LINK (ILLUSTRATIVE)</text>
      <circle class="pkt-norm" r="6">
        <animateMotion dur="4.6s" repeatCount="indefinite" rotate="auto"
          path="M 96 88 C 180 42, 260 42, 344 88"/>
      </circle>
      <circle r="3" fill="#64748b" opacity="0.7">
        <animateMotion dur="3.2s" repeatCount="indefinite" begin="0.8s"
          path="M 96 88 C 180 42, 260 42, 344 88"/>
      </circle>
      <text x="220" y="152" text-anchor="middle" class="demo-lat demo-lat--norm">~100+ ms</text>
      <text x="220" y="168" text-anchor="middle" class="demo-foot">Higher delay · commands not prioritized</text>
    </svg>
  </div>
"""
    purllc = """
  <div class="surgery-panel">
    <span class="panel-badge panel-badge--urllc">With URLLC slice</span>
    <svg viewBox="0 0 440 188" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gUrllcAnimR" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" style="stop-color:#0ea5e9;stop-opacity:0.2"/>
          <stop offset="100%" style="stop-color:#a78bfa;stop-opacity:0.18"/>
        </linearGradient>
      </defs>
      <rect width="440" height="188" fill="url(#gUrllcAnimR)" rx="8"/>
      <text x="220" y="22" text-anchor="middle" class="demo-h">URLLC slice (priority)</text>
      <text x="220" y="38" text-anchor="middle" class="demo-foot">Surgical control jumps the queue · protected path</text>
      <!-- Surgeon: simple person + computer (URLLC accents) -->
      <rect x="18" y="52" width="78" height="58" rx="6" fill="#111827" stroke="#0369a1"/>
      <g transform="translate(18,52)">
        <circle cx="22" cy="17" r="8" fill="#0c4a6e" stroke="#38bdf8" stroke-width="1.2"/>
        <path d="M 10 28 Q 22 22 34 28 L 32 48 L 12 48 Z" fill="#075985" stroke="#38bdf8" stroke-width="1"/>
        <rect x="36" y="9" width="34" height="28" rx="2" fill="#0f172a" stroke="#0ea5e9" stroke-width="1"/>
        <rect x="39" y="12" width="28" height="19" rx="1" fill="#020617" stroke="#0369a1"/>
        <rect x="48" y="37" width="10" height="5" rx="1" fill="#0c4a6e" stroke="#38bdf8"/>
        <rect x="42" y="42" width="22" height="3" rx="1" fill="#0c4a6e" stroke="#0ea5e9"/>
      </g>
      <text x="57" y="124" text-anchor="middle" class="demo-lbl">Surgeon</text>
      <!-- Surgical robot arm (URLLC) -->
      <rect x="344" y="52" width="78" height="58" rx="6" fill="#111827" stroke="#0369a1"/>
      <g transform="translate(344,52)">
        <ellipse cx="56" cy="51" rx="15" ry="3.8" fill="#0c4a6e" stroke="#0369a1"/>
        <rect x="50" y="30" width="12" height="22" rx="2" fill="#1e293b" stroke="#0ea5e9"/>
        <circle cx="56" cy="30" r="4" fill="#0369a1" stroke="#38bdf8"/>
        <path d="M 56 30 L 38 20" stroke="#38bdf8" stroke-width="3.2" stroke-linecap="round"/>
        <circle cx="38" cy="20" r="3.2" fill="#0ea5e9"/>
        <path d="M 38 20 L 16 28" stroke="#7dd3fc" stroke-width="2.6" stroke-linecap="round"/>
        <circle cx="16" cy="28" r="2.8" fill="#22d3ee"/>
        <path d="M 10 24 L 6 28 L 10 32 M 14 24 L 10 28 L 14 32" fill="none" stroke="#e0f2fe" stroke-width="1.6" stroke-linecap="round"/>
        <circle cx="8" cy="28" r="3.5" fill="none" stroke="#22d3ee" stroke-width="1.2"/>
      </g>
      <text x="383" y="124" text-anchor="middle" class="demo-lbl">Robot</text>
      <path class="beam-urllc" d="M 96 88 C 180 42, 260 42, 344 88"/>
      <text x="220" y="72" text-anchor="middle" class="demo-lat-sub">CONTROL LINK (ILLUSTRATIVE)</text>
      <circle class="pkt-urllc" r="7">
        <animateMotion dur="1.35s" repeatCount="indefinite" rotate="auto"
          path="M 96 88 C 180 42, 260 42, 344 88"/>
      </circle>
      <text x="220" y="152" text-anchor="middle" class="demo-lat demo-lat--urllc">&lt;1 ms</text>
      <text x="220" y="168" text-anchor="middle" class="demo-foot">Lower latency · reliable control channel</text>
    </svg>
  </div>
"""
    return css, pnorm, purllc


# ── Global styles ──
st.markdown(
    """
    <style>
    @keyframes chartIn {
        from { opacity: 0.35; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    [data-testid="stPlotlyChart"] { animation: chartIn 0.55s ease-out both; }

    </style>
    """,
    unsafe_allow_html=True,
)


# ── Shared URLLC landing/wizard radar layer (st.html only — same visuals as landing) ──
_URLLC_LP_FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Exo+2:wght@300;400;700;800&display=swap');"
)

_URLLC_LP_SCENE_CSS = """
/* ── Background gradient ── */
.lp-bg{
  position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(ellipse 80% 70% at 50% 42%,rgba(0,160,255,.08) 0%,transparent 62%),
    radial-gradient(ellipse 55% 40% at 80% 80%,rgba(100,60,240,.06) 0%,transparent 50%),
    linear-gradient(168deg,#060d1f 0%,#03070f 50%,#080518 100%)}

/* ── Ring container ── */
.lp-rings{position:fixed;inset:0;z-index:1;pointer-events:none;overflow:hidden}

/* ── Rings ── */
.lp-ring{
  position:absolute;top:50%;left:50%;
  width:120px;height:120px;
  border-radius:50%;
  border:1.5px solid rgba(0,210,255,.72);
  transform:translate(-50%,-50%) scale(.08);
  box-shadow:0 0 10px rgba(0,190,255,.25);
  animation:ringOut 4.8s ease-out infinite}
.lp-ring--2{animation-delay:1.2s;border-color:rgba(0,195,255,.6)}
.lp-ring--3{animation-delay:2.4s;border-color:rgba(0,175,255,.48)}
.lp-ring--4{animation-delay:3.6s;border-color:rgba(0,155,255,.32)}
@keyframes ringOut{
  0%  {transform:translate(-50%,-50%) scale(.08);opacity:.95}
  100%{transform:translate(-50%,-50%) scale(17);opacity:0}}

/* ── Radar sweep ── */
.lp-sweep{
  position:absolute;top:50%;left:50%;
  width:70vmax;height:70vmax;
  transform-origin:0% 0%;
  background:conic-gradient(from 0deg,transparent 268deg,rgba(0,220,255,.055) 360deg);
  animation:sweepRot 6s linear infinite;z-index:2}
@keyframes sweepRot{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}

/* ── Cross-hair ── */
.lp-cross{position:absolute;inset:0;pointer-events:none}
.lp-cross::before{content:'';position:absolute;top:50%;left:0;right:0;height:1px;background:rgba(0,200,255,.1)}
.lp-cross::after{content:'';position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(0,200,255,.1)}

/* ── Center dot ── */
.lp-dot{
  position:absolute;top:50%;left:50%;
  width:14px;height:14px;
  transform:translate(-50%,-50%);
  border-radius:50%;
  background:rgba(0,220,255,.98);
  box-shadow:0 0 12px 3px rgba(0,220,255,1),0 0 32px rgba(0,180,255,.55);
  animation:dotPulse 2s ease-in-out infinite;z-index:3}
@keyframes dotPulse{
  0%,100%{transform:translate(-50%,-50%) scale(1);opacity:1}
  50%    {transform:translate(-50%,-50%) scale(1.55);opacity:.55}}

/* ── Top bar (fixed) ── */
.lp-topbar{
  position:fixed;top:0;left:0;right:0;z-index:50;
  padding:.85rem 1.5rem;display:flex;align-items:center;
  justify-content:space-between;pointer-events:none;
  animation:fadeUp .9s ease-out both}
.lp-topbar-title{
  font-family:"Rajdhani",system-ui,sans-serif;
  font-size:clamp(.68rem,1.8vw,.85rem);font-weight:700;
  letter-spacing:.38em;text-transform:uppercase;color:rgba(0,210,255,.88)}
.lp-topbar-badge{
  font-size:.58rem;font-weight:600;letter-spacing:.28em;
  padding:3px 10px;border-radius:4px;
  border:1px solid rgba(0,210,255,.35);color:rgba(0,210,255,.65)}
"""

_URLLC_LP_SCENE_HTML = """
<div class="lp-bg"></div>
<div class="lp-rings">
  <div class="lp-cross"></div>
  <div class="lp-sweep"></div>
  <div class="lp-ring lp-ring--1"></div>
  <div class="lp-ring lp-ring--2"></div>
  <div class="lp-ring lp-ring--3"></div>
  <div class="lp-ring lp-ring--4"></div>
  <div class="lp-dot"></div>
</div>
<div class="lp-topbar">
  <span class="lp-topbar-title">URLLC Healthcare Simulation</span>
  <span class="lp-topbar-badge">SimPy &nbsp;·&nbsp; 5G MODEL</span>
</div>
"""


def _urllc_lp_chrome_viewport_css(*, wizard: bool) -> str:
    bc_overflow = (
        "overflow-y:auto!important;overflow-x:hidden!important"
        if wizard
        else "overflow:hidden!important"
    )
    return f"""
header[data-testid="stHeader"],footer,[data-testid="stDecoration"],
[data-testid="collapsedControl"],section[data-testid="stSidebar"]{{display:none!important}}

html,body{{overflow:hidden!important;height:100%!important;margin:0!important}}
.stApp{{background:#04091a!important;height:100dvh!important;overflow:hidden!important}}
.stApp [data-testid="stAppViewContainer"],
.stApp [data-testid="stAppViewContainer"]>div{{height:100dvh!important;overflow:hidden!important}}
section.main{{height:100dvh!important;overflow:hidden!important}}
section.main>div.block-container{{
  height:100dvh!important;max-height:100dvh!important;{bc_overflow};
  padding:0!important;max-width:100%!important;box-sizing:border-box!important;
  background:transparent!important}}
"""


def _urllc_wizard_lp_sthtml() -> str:
    wiz_layout = """
/* One scroll parent only: .block-container. Avoid max-height + overflow on this block or the
   primary button (SIMULATE) sits below the fold behind a harsh native scrollbar. */
[data-testid="stVerticalBlock"]{
  min-height:100dvh!important;height:auto!important;
  display:flex!important;flex-direction:column!important;
  justify-content:flex-start!important;align-items:center!important;
  padding:2.5rem 1rem 2.5rem!important;overflow:visible!important;
  box-sizing:border-box!important;position:relative!important;z-index:15!important}
[data-testid="stVerticalBlock"]>div{
  flex:0 0 auto!important;width:100%!important;max-width:100%!important;
  align-self:stretch!important}
[data-testid="stHtml"]{height:0!important;overflow:visible!important}
"""
    return f"""<style>
{_URLLC_LP_FONT_IMPORT}
{_urllc_lp_chrome_viewport_css(wizard=True)}
{wiz_layout}
{_URLLC_LP_SCENE_CSS}
@keyframes fadeUp{{from{{opacity:0}}to{{opacity:1}}}}
</style>
{_URLLC_LP_SCENE_HTML}
"""


def _urllc_landing_lp_sthtml() -> str:
    landing_layout = """
/* ── Vertical block: full-screen flex column, centered ── */
[data-testid="stVerticalBlock"]{
  height:100dvh!important;overflow:hidden!important;
  display:flex!important;flex-direction:column!important;
  justify-content:center!important;align-items:center!important;
  gap:1.75rem!important;padding:3.5rem 1rem 2rem!important;
  box-sizing:border-box!important;position:relative!important;z-index:10!important}
[data-testid="stVerticalBlock"]>div{
  flex:0 0 auto!important;display:flex!important;
  flex-direction:column!important;align-items:center!important;
  width:100%!important;max-width:100%!important}

/* ── stHtml wrapper: no in-flow height (all content is fixed) ── */
[data-testid="stHtml"]{height:0!important;overflow:visible!important}

/* ── stHorizontalBlock (columns): zero out, button is fixed ── */
[data-testid="stHorizontalBlock"]{height:0!important;overflow:visible!important}

/* ── Headline block: fixed-centered ── */
.lp-center{
  position:fixed;top:50%;left:0;right:0;
  transform:translateY(-55%);
  z-index:10;display:flex;flex-direction:column;
  align-items:center;text-align:center;
  pointer-events:none;
  animation:riseUp 1s cubic-bezier(.16,1,.3,1) .1s both}
.lp-headline{
  font-family:"Exo 2","Rajdhani",system-ui,sans-serif;
  font-weight:800;font-size:clamp(1.55rem,5.5vw,3rem);
  line-height:1.1;letter-spacing:-.02em;color:#eef6ff;
  margin:0}
.lp-headline .cy{color:#00d4ff;text-shadow:0 0 28px rgba(0,200,255,.35)}
.lp-sub{
  font-family:"Exo 2",system-ui,sans-serif;
  font-size:clamp(.85rem,1.9vw,.98rem);font-weight:300;color:#7bafc8;
  max-width:30rem;line-height:1.6;margin:.65rem 0 0;
  animation:fadeUp 1s ease-out .3s both}

/* ── Button: fixed, just below center ── */
html body .stApp [data-testid="stButton"],
html body .stApp div.stButton{
  position:fixed!important;
  top:calc(50% + 175px)!important;left:50%!important;
  transform:translateX(-50%)!important;
  z-index:20!important;width:auto!important}

@keyframes fadeUp{from{opacity:0}to{opacity:1}}
@keyframes riseUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}

/* ── ENTER SIMULATION button (beats Streamlit primary theme) ── */
@keyframes btnGlow{
  0%,100%{box-shadow:
    inset 0 0 0 1px rgba(155,220,255,.16),
    0 0 26px rgba(0,158,255,.46),
    0 0 60px rgba(0,108,255,.26),
    0 10px 30px rgba(0,0,0,.52)}
  50%{box-shadow:
    inset 0 0 0 1px rgba(200,242,255,.28),
    0 0 42px rgba(0,208,255,.65),
    0 0 90px rgba(50,155,255,.38),
    0 10px 34px rgba(0,0,0,.52)}}
html body .stApp [data-testid="stButton"]>button,
html body .stApp div.stButton>button{
  min-height:3.6rem!important;
  padding:0 2.5rem!important;min-width:16rem!important;
  font-family:"Rajdhani","Exo 2",system-ui,sans-serif!important;
  font-size:1.06rem!important;font-weight:700!important;
  letter-spacing:.3em!important;text-transform:uppercase!important;
  color:#dff6ff!important;border-radius:14px!important;
  border:1px solid rgba(105,200,255,.68)!important;
  background:linear-gradient(155deg,
    rgba(0,145,255,.48) 0%,rgba(0,80,222,.32) 50%,rgba(18,48,168,.44) 100%)!important;
  background-color:rgba(4,20,62,.42)!important;
  backdrop-filter:blur(20px) saturate(1.5)!important;
  -webkit-backdrop-filter:blur(20px) saturate(1.5)!important;
  box-shadow:
    inset 0 0 0 1px rgba(155,220,255,.16),
    0 0 26px rgba(0,158,255,.46),
    0 0 60px rgba(0,108,255,.26),
    0 10px 30px rgba(0,0,0,.52)!important;
  animation:btnGlow 2.5s ease-in-out infinite,
    riseUp .9s cubic-bezier(.16,1,.3,1) .45s both!important;
  transition:transform .18s ease,filter .18s ease,border-color .18s ease!important;
  cursor:pointer!important;position:relative!important;z-index:20!important}
html body .stApp [data-testid="stButton"]>button:hover,
html body .stApp div.stButton>button:hover{
  transform:scale(1.05) translateY(-3px)!important;
  filter:brightness(1.15)!important;
  border-color:rgba(180,240,255,.95)!important}
"""
    hero = """
<div class="lp-center">
  <h1 class="lp-headline">5G Network Slicing<br><span class="cy">URLLC</span></h1>
  <p class="lp-sub">Healthcare Simulation</p>
</div>
"""
    return f"""<style>
{_URLLC_LP_FONT_IMPORT}
{_urllc_lp_chrome_viewport_css(wizard=False)}
{landing_layout}
{_URLLC_LP_SCENE_CSS}
</style>
{_URLLC_LP_SCENE_HTML}
{hero}
"""


# ═══════════════════════════════════════════════════════════════════════════
# LANDING
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "landing":
    st.html(_urllc_landing_lp_sthtml())

    _, _mid, _ = st.columns([1, 1.6, 1])
    with _mid:
        if st.button("ENTER SIMULATION", type="primary", key="lp_enter", use_container_width=True):
            st.session_state.phase = "wizard"
            st.session_state.wiz_step = 0
            st.rerun()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# RESULTS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "results":
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }

        .tc-wrap { margin: 0.5rem 0 1.5rem 0; overflow-x: auto; }
        .traffic-matrix {
          width: 100%; min-width: 640px; border-collapse: separate; border-spacing: 0;
          font-size: 1.05rem; border-radius: 14px; overflow: hidden;
          box-shadow: 0 4px 24px rgba(0,0,0,0.25);
          border: 1px solid #334155;
        }
        .traffic-matrix thead th {
          background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
          color: #e2e8f0; font-weight: 700; text-align: left; padding: 16px 14px;
          font-size: 0.95rem; letter-spacing: 0.02em; border-bottom: 2px solid #38bdf8;
        }
        .traffic-matrix .tc-thsub { font-weight: 500; font-size: 0.78rem; color: #94a3b8; letter-spacing: 0; }
        .traffic-matrix thead th.tc-th--accent { color: #22d3ee; }
        .traffic-matrix thead th.tc-th--accent .tc-thsub { color: #67e8f9; opacity: 0.9; }
        .traffic-matrix tbody tr { background: #111827; }
        .traffic-matrix tbody tr:nth-child(even) { background: #0f172a; }
        .traffic-matrix tbody tr:hover { background: #1e293b; }
        .traffic-matrix td { padding: 18px 14px; border-bottom: 1px solid #1e293b; vertical-align: middle; }
        .traffic-matrix tbody tr:last-child td { border-bottom: none; }
        .tc-role { color: #94a3b8; font-size: 0.98rem; max-width: 220px; line-height: 1.35; }
        .tc-num { font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
          font-size: 1.2rem; font-weight: 600; color: #e2e8f0; white-space: nowrap; }
        .tc-num--accent { color: #22d3ee; text-shadow: 0 0 20px rgba(34,211,238,0.25); }
        .tc-tag { display: inline-block; padding: 6px 12px; border-radius: 8px; font-weight: 800;
          font-size: 0.88rem; letter-spacing: 0.06em; }
        .tc-tag--urllc { background: rgba(34,211,238,0.15); color: #22d3ee; border: 1px solid #0891b2; }
        .tc-tag--embb { background: rgba(244,114,182,0.12); color: #f472b6; border: 1px solid #be185d; }
        .tc-tag--iot { background: rgba(167,139,250,0.12); color: #c4b5fd; border: 1px solid #7c3aed; }
        .tc-foot { margin-top: 12px; font-size: 0.85rem; color: #64748b; line-height: 1.5; max-width: 920px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    res_normal = st.session_state.res_normal
    res_urllc = st.session_state.res_urllc
    d, L, q = st.session_state.wiz_dur, st.session_state.wiz_load, st.session_state.wiz_queue

    cfg = plotly_chart_config()

    top_l, top_r = st.columns([1, 1])
    with top_l:
        st.title("URLLC slice for remote healthcare")
        st.caption(f"Results · duration **{d}** · load **{L:.2f}** · queue **{q}**")
    with top_r:
        st.write("")
        st.write("")
        if st.button("← New simulation", type="secondary"):
            _reset_wizard()
            st.rerun()

    show_anim = st.toggle("Show Kerala → Delhi link animation", value=False)
    enable_urllc = st.toggle("Enable URLLC", value=False)

    results_list_cmp = [res_normal, res_urllc] if enable_urllc else [res_normal]
    tab_cmp = comparison_table(results_list_cmp)
    cats_cmp = mode_labels(results_list_cmp)
    tab_u_only = comparison_table([res_urllc])
    cats_u = mode_labels([res_urllc])
    key_base = f"{d}_{L}_{q}_u{int(enable_urllc)}"

    _demo_css, _panel_norm, _panel_urllc = _demo_assets()
    if show_anim:
        solo = "" if enable_urllc else "surgery-panel--solo"
        norm_html = _panel_norm.replace("SURGEON_SOLO_CLASS", solo)
        body = (
            f'<p style="text-align:center;margin:0 0 10px 0;color:#cbd5e1;font-size:14px;font-weight:600;">'
            f'Remote surgery link · Kerala → Delhi</p><div class="surgery-dual-row">{norm_html}'
        )
        if enable_urllc:
            body += _panel_urllc
        body += "</div>"
        st.markdown(_demo_css + '<div class="surgery-dual-wrap">' + body + "</div>", unsafe_allow_html=True)
        if not enable_urllc:
            st.caption("Turn on **Enable URLLC** to add the priority-link (URLLC slice) panel beside the normal link.")

    n_ul = res_normal["by_type"]["URLLC"]
    u_ul = res_urllc["by_type"]["URLLC"]
    if enable_urllc and n_ul.get("avg_latency") and u_ul.get("avg_latency") and n_ul["avg_latency"] > 0:
        pct = (1.0 - u_ul["avg_latency"] / n_ul["avg_latency"]) * 100.0
        st.success(
            f"**URLLC surgical traffic:** latency **{_fmt_latency(n_ul.get('avg_latency'))}** → "
            f"**{_fmt_latency(u_ul.get('avg_latency'))}** (~**{max(0, pct):.0f}%** lower with slice). "
            f"Loss **{_fmt_loss_pct(n_ul['packet_loss_rate'])}** → **{_fmt_loss_pct(u_ul['packet_loss_rate'])}**."
        )

    st.subheader("Results by traffic class")
    st.caption(
        "Compare how each 5G-style traffic type behaves. "
        "Turn on **Enable URLLC** to see no-slice vs URLLC-slice columns side by side."
    )
    st.markdown(_traffic_class_matrix_html(enable_urllc, res_normal, res_urllc), unsafe_allow_html=True)

    st.subheader("Charts — Normal vs URLLC (comparison)" if enable_urllc else "Charts — normal network")
    ch1, ch2, ch3 = st.columns(3)
    ch1.plotly_chart(
        plotly_grouped_bar(
            cats_cmp,
            tab_cmp["avg_latency"],
            "Average latency" if enable_urllc else "Average latency (normal)",
            "Latency (sim units)",
        ),
        use_container_width=True,
        config=cfg,
        key=f"cmp_lat_{key_base}",
    )
    ch2.plotly_chart(
        plotly_grouped_bar(
            cats_cmp,
            tab_cmp["packet_loss_pct"],
            "Packet loss" if enable_urllc else "Packet loss (normal)",
            "Loss (%)",
        ),
        use_container_width=True,
        config=cfg,
        key=f"cmp_loss_{key_base}",
    )
    ch3.plotly_chart(
        plotly_grouped_bar(
            cats_cmp,
            tab_cmp["reliability_pct"],
            "Reliability" if enable_urllc else "Reliability (normal)",
            "Reliable (%)",
            [0, 105],
        ),
        use_container_width=True,
        config=cfg,
        key=f"cmp_rel_{key_base}",
    )

    if enable_urllc:
        st.subheader("Charts — URLLC slice only")
        st.caption("Same run as **URLLC slice ON** above; slice metrics in isolation.")
        u1, u2, u3 = st.columns(3)
        u1.plotly_chart(
            plotly_grouped_bar(cats_u, tab_u_only["avg_latency"], "Latency (URLLC slice)", "Latency (sim units)"),
            use_container_width=True,
            config=cfg,
            key=f"uonly_lat_{key_base}",
        )
        u2.plotly_chart(
            plotly_grouped_bar(cats_u, tab_u_only["packet_loss_pct"], "Loss (URLLC slice)", "Loss (%)"),
            use_container_width=True,
            config=cfg,
            key=f"uonly_loss_{key_base}",
        )
        u3.plotly_chart(
            plotly_grouped_bar(cats_u, tab_u_only["reliability_pct"], "Reliability (URLLC slice)", "Reliable (%)", [0, 105]),
            use_container_width=True,
            config=cfg,
            key=f"uonly_rel_{key_base}",
        )

    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# BOOT (fullscreen futuristic loader — no balloons)
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "boot":
    st.markdown(
        """
        <style>
        #boot-hide-header ~ * { } 
        header[data-testid="stHeader"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        footer { visibility: hidden !important; height: 0 !important; }
        </style>
        <div id="boot-hide-header"></div>
        <div class="boot-full">
          <div class="boot-grid"></div>
          <div class="boot-scan"></div>
          <div class="boot-core">
            <div class="boot-orbit boot-orbit--a"></div>
            <div class="boot-orbit boot-orbit--b"></div>
            <div class="boot-orbit boot-orbit--c"></div>
            <div class="boot-dot"></div>
          </div>
          <p class="boot-brand">URLLC · 5G SIMULATION</p>
          <h1 class="boot-h1">Initializing network model</h1>
          <p class="boot-lines">Slicing control plane · Mapping Kerala ↔ Delhi · Resolving queue discipline</p>
          <div class="boot-bar"><div class="boot-bar-fill"></div></div>
        </div>
        <style>
        .boot-full {
          position: fixed; inset: 0; z-index: 99999;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          background: radial-gradient(ellipse 80% 60% at 50% 40%, #0c1929 0%, #030712 65%, #000 100%);
          font-family: "Segoe UI", system-ui, sans-serif;
        }
        .boot-grid {
          position: absolute; inset: 0; opacity: 0.12;
          background-image:
            linear-gradient(rgba(34,211,238,0.35) 1px, transparent 1px),
            linear-gradient(90deg, rgba(34,211,238,0.35) 1px, transparent 1px);
          background-size: 48px 48px;
          animation: bootGridDrift 20s linear infinite;
        }
        @keyframes bootGridDrift {
          from { background-position: 0 0, 0 0; } to { background-position: 48px 48px, 48px 48px; }
        }
        .boot-scan {
          position: absolute; inset: 0;
          background: linear-gradient(180deg, transparent 0%, rgba(34,211,238,0.06) 50%, transparent 100%);
          background-size: 100% 220%;
          animation: bootScanMove 2.8s ease-in-out infinite;
          pointer-events: none;
        }
        @keyframes bootScanMove {
          0%, 100% { background-position: 0 -100%; } 50% { background-position: 0 100%; }
        }
        .boot-core { position: relative; width: 140px; height: 140px; margin-bottom: 28px; }
        .boot-orbit {
          position: absolute; inset: 0; border-radius: 50%;
          border: 2px solid transparent;
          animation: bootSpin 3s linear infinite;
        }
        .boot-orbit--a {
          border-top-color: #22d3ee; border-right-color: rgba(34,211,238,0.3);
          animation-duration: 1.2s;
        }
        .boot-orbit--b {
          inset: 12px; border-bottom-color: #a78bfa; border-left-color: rgba(167,139,250,0.35);
          animation-duration: 1.8s; animation-direction: reverse;
        }
        .boot-orbit--c {
          inset: 28px; border-top-color: rgba(244,114,182,0.6);
          animation-duration: 2.4s;
        }
        @keyframes bootSpin { to { transform: rotate(360deg); } }
        .boot-dot {
          position: absolute; left: 50%; top: 50%; width: 14px; height: 14px; margin: -7px 0 0 -7px;
          border-radius: 50%;
          background: #22d3ee;
          box-shadow: 0 0 24px #22d3ee, 0 0 48px rgba(34,211,238,0.5);
          animation: bootPulseDot 1.2s ease-in-out infinite;
        }
        @keyframes bootPulseDot {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.15); opacity: 0.85; }
        }
        .boot-brand {
          color: #38bdf8; font-size: 0.72rem; letter-spacing: 0.42em; font-weight: 700;
          margin: 0 0 8px 0; opacity: 0.9;
        }
        .boot-h1 {
          color: #f1f5f9; font-size: 1.35rem; font-weight: 700; margin: 0 0 10px 0;
          letter-spacing: 0.06em; text-align: center;
        }
        .boot-lines {
          color: #64748b; font-size: 0.82rem; max-width: 320px; text-align: center;
          line-height: 1.5; margin: 0 0 28px 0;
        }
        .boot-bar {
          width: min(280px, 70vw); height: 3px; border-radius: 3px;
          background: rgba(51,65,85,0.6); overflow: hidden;
        }
        .boot-bar-fill {
          height: 100%; width: 40%;
          background: linear-gradient(90deg, #0e7490, #22d3ee, #a78bfa);
          border-radius: 3px;
          animation: bootBarSlide 1.1s ease-in-out infinite;
        }
        @keyframes bootBarSlide {
          0% { transform: translateX(-100%); } 100% { transform: translateX(350%); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    d = float(st.session_state.wiz_dur)
    L = float(st.session_state.wiz_load)
    q = int(st.session_state.wiz_queue)
    time.sleep(1.35)
    st.session_state.res_normal = run_scenario(d, L, False, q, DEFAULT_SEED)
    st.session_state.res_urllc = run_scenario(d, L, True, q, DEFAULT_SEED)
    st.session_state.phase = "results"
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# WIZARD
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "wizard":
    st.html(_urllc_wizard_lp_sthtml())

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    /* Single themed scrollbar on main (only if content exceeds viewport) */
    section.main > div.block-container {
      scrollbar-width: thin;
      scrollbar-color: rgba(34, 211, 238, 0.45) rgba(15, 23, 42, 0.6);
    }
    section.main > div.block-container::-webkit-scrollbar { width: 8px; }
    section.main > div.block-container::-webkit-scrollbar-track {
      background: rgba(15, 23, 42, 0.5);
      border-radius: 4px;
    }
    section.main > div.block-container::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, rgba(34,211,238,0.5), rgba(56,189,248,0.35));
      border-radius: 4px;
    }

    /* Centered presenter card feel */
    .wiz-outer .block-container { padding-top: 1.25rem !important; }

    /* Step dots */
    .wiz-dots { display: flex; justify-content: center; gap: 8px; margin: 0 0 1.25rem 0; }
    .wiz-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #334155; transition: background 0.2s, transform 0.2s;
    }
    .wiz-dot--on {
      background: linear-gradient(135deg, #22d3ee, #a78bfa);
      transform: scale(1.25);
      box-shadow: 0 0 12px rgba(34,211,238,0.45);
    }

    /* Wizard: compact Back / Next (secondary) */
    div[data-testid="column"]:has(.wiz-card-anchor) div.stButton > button[kind="secondary"] {
      min-height: 2.2rem !important;
      padding: 0.32rem 1.05rem !important;
      font-size: 0.8125rem !important;
      font-weight: 600 !important;
      border-radius: 10px !important;
      width: auto !important;
      background: rgba(30,41,59,0.9) !important;
      color: #e2e8f0 !important;
      border: 1px solid #475569 !important;
    }
    div[data-testid="column"]:has(.wiz-card-anchor) div.stButton > button[kind="secondary"]:hover {
      border-color: #64748b !important;
      background: rgba(51,65,85,0.95) !important;
    }

    /* SIMULATE — only primary on this flow */
    div[data-testid="column"]:has(.wiz-card-anchor) div.stButton > button[kind="primary"] {
      min-height: 3.4rem !important;
      padding: 0.9rem 1.25rem !important;
      font-size: 1.06rem !important;
      font-weight: 800 !important;
      letter-spacing: 0.24em !important;
      border-radius: 14px !important;
      width: 100% !important;
      background: linear-gradient(110deg, #0e7490, #22d3ee, #0891b2, #22d3ee, #0e7490) !important;
      background-size: 220% auto !important;
      border: 2px solid #7dd3fc !important;
      color: #020617 !important;
      box-shadow: 0 0 28px rgba(34,211,238,0.35), 0 0 60px rgba(34,211,238,0.12) !important;
      animation: wizSimPulse 2.2s ease-in-out infinite, wizSimScan 4s linear infinite !important;
    }
    div[data-testid="column"]:has(.wiz-card-anchor) div.stButton > button[kind="primary"]:hover {
      border-color: #e0f2fe !important;
      filter: brightness(1.06);
    }
    @keyframes wizSimPulse {
      0%, 100% { box-shadow: 0 0 24px rgba(34,211,238,0.35), 0 0 56px rgba(34,211,238,0.12); }
      50% { box-shadow: 0 0 40px rgba(34,211,238,0.65), 0 0 90px rgba(34,211,238,0.22); }
    }
    @keyframes wizSimScan {
      0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; }
    }

    /* Card panel around centered column (above fixed radar layer) */
    div[data-testid="column"]:has(.wiz-card-anchor) {
      position: relative;
      z-index: 24;
      background: linear-gradient(160deg, rgba(15,23,42,0.88) 0%, rgba(8,12,22,0.93) 100%);
      border: 1px solid rgba(56,189,248,0.22);
      border-radius: 20px;
      padding: 1.5rem 1.65rem 1.65rem 1.65rem !important;
      box-shadow: 0 4px 32px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.03) inset;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_, wiz_mid, _ = st.columns([1, 1.35, 1])

with wiz_mid:
    st.markdown('<span class="wiz-card-anchor"></span>', unsafe_allow_html=True)
    step = st.session_state.wiz_step
    dots_html = "".join(
        f'<span class="wiz-dot{" wiz-dot--on" if i == step else ""}"></span>' for i in range(4)
    )
    st.markdown(f'<div class="wiz-dots">{dots_html}</div>', unsafe_allow_html=True)

    st.markdown(
        '<p style="text-align:center;margin:0 0 0.35rem 0;color:#94a3b8;font-size:0.75rem;letter-spacing:0.12em;">'
        "REMOTE HEALTHCARE · 5G</p>",
        unsafe_allow_html=True,
    )
    st.title("URLLC slice for remote healthcare")
    st.caption("Step-by-step setup — use **Back** / **Next**, then **SIMULATE**.")

    if step == 0:
        st.markdown("### Step 1 — Duration")
        st.session_state.wiz_dur = st.slider(
            "Simulation time (abstract units)",
            min_value=20,
            max_value=100,
            value=int(st.session_state.wiz_dur),
            step=10,
            key="slider_dur",
        )
        _, r_nav, _ = st.columns([1, 1, 1])
        with r_nav:
            if st.button("Next →", type="secondary", key="w0n", use_container_width=False):
                st.session_state.wiz_step = 1
                st.rerun()

    elif step == 1:
        st.markdown("### Step 2 — Network load")
        st.session_state.wiz_load = st.slider(
            "Traffic load (higher = busier)",
            min_value=0.3,
            max_value=1.0,
            value=float(st.session_state.wiz_load),
            step=0.05,
            key="slider_load",
        )
        c1, c2, _ = st.columns([0.42, 0.42, 1.6])
        with c1:
            if st.button("← Back", key="w1b", use_container_width=False):
                st.session_state.wiz_step = 0
                st.rerun()
        with c2:
            if st.button("Next →", type="secondary", key="w1n", use_container_width=False):
                st.session_state.wiz_step = 2
                st.rerun()

    elif step == 2:
        st.markdown("### Step 3 — Queue size")
        st.session_state.wiz_queue = st.slider(
            "Max waiting packets at the link",
            min_value=3,
            max_value=20,
            value=int(st.session_state.wiz_queue),
            step=1,
            key="slider_queue",
        )
        c1, c2, _ = st.columns([0.42, 0.42, 1.6])
        with c1:
            if st.button("← Back", key="w2b", use_container_width=False):
                st.session_state.wiz_step = 1
                st.rerun()
        with c2:
            if st.button("Next →", type="secondary", key="w2n", use_container_width=False):
                st.session_state.wiz_step = 3
                st.rerun()

    elif step == 3:
        st.markdown("### Step 4 — Run simulation")
        st.markdown(
            f'<p style="color:#cbd5e1;font-size:0.9rem;line-height:1.55;margin:0.5rem 0 1rem 0;">'
            f"<b>Duration</b> {st.session_state.wiz_dur} · "
            f"<b>Load</b> {st.session_state.wiz_load:.2f} · "
            f"<b>Queue</b> {st.session_state.wiz_queue}</p>",
            unsafe_allow_html=True,
        )
        c_back, c_run = st.columns([1, 1.15])
        with c_back:
            if st.button("← Back", key="w3b", use_container_width=True):
                st.session_state.wiz_step = 2
                st.rerun()
        with c_run:
            if st.button("SIMULATE", type="primary", key="w3sim", use_container_width=True):
                st.session_state.phase = "boot"
                st.rerun()
        st.caption("Runs both **Normal** and **URLLC slice** models with the same parameters.")
