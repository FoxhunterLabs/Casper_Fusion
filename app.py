"""
CASPER_FUSION — Streamlit Application
====================================

Thin UI wrapper for Casper_Fusion.
All simulation, fusion, and governance logic lives in casper/.
"""

import time
import streamlit as st
import pandas as pd
import pydeck as pdk

from casper.config import FusionConfig
from casper.state import EngineState
from casper.step_engine import StepEngine
from casper.presets import AO_PRESETS, ENVIRONMENTS, ENVELOPES
from casper.visualization.terrain import TerrainGenerator


# ============================================================
# STREAMLIT SETUP
# ============================================================

st.set_page_config(
    page_title="CASPER_FUSION — Synthetic Recon Console",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE INIT
# ============================================================

def init_state():
    config = FusionConfig()
    state = EngineState(config=config)
    state.run_id = int(time.time() * 1000)
    state.rng_seed = state.run_id % (2**32)
    state.ao = AO_PRESETS["Kharkiv (synthetic)"]
    return state


if "engine_state" not in st.session_state:
    st.session_state.engine_state = init_state()

if "running" not in st.session_state:
    st.session_state.running = False


state: EngineState = st.session_state.engine_state
step_engine = StepEngine(state.config)
terrain_gen = TerrainGenerator()


# ============================================================
# HEADER
# ============================================================

c1, c2, c3 = st.columns([4, 1, 1])

with c1:
    st.markdown("## CASPER_FUSION — Synthetic Recon Governance Console")
    st.caption("Multi-sensor fusion • Deterministic • Audit-bound • Recon-only")

with c2:
    st.markdown(
        f"<div style='font-family:monospace;font-size:12px;text-align:center;'>"
        f"RUN<br/>{state.run_id}</div>",
        unsafe_allow_html=True,
    )

with c3:
    status = "🟢 RUNNING" if st.session_state.running else "⏸ PAUSED"
    st.markdown(f"<div style='text-align:center;'>{status}</div>", unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# SIDEBAR CONTROLS
# ============================================================

with st.sidebar:
    st.title("Controls")

    if st.button("▶ Start", use_container_width=True):
        st.session_state.running = True

    if st.button("⏸ Pause", use_container_width=True):
        st.session_state.running = False

    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.engine_state.reset()
        st.session_state.running = False
        st.rerun()

    st.markdown("---")
    st.subheader("Scenario")

    state.env_name = st.selectbox(
        "Environment",
        list(ENVIRONMENTS.keys()),
        index=list(ENVIRONMENTS.keys()).index(state.env_name),
    )

    state.envelope_name = st.selectbox(
        "Envelope",
        list(ENVELOPES.keys()),
        index=list(ENVELOPES.keys()).index(state.envelope_name),
    )

    ao_key = st.selectbox(
        "Area of Operations",
        list(AO_PRESETS.keys()),
        index=list(AO_PRESETS.keys()).index(next(k for k, v in AO_PRESETS.items() if v == state.ao)),
    )
    state.ao = AO_PRESETS[ao_key]


# ============================================================
# STEP EXECUTION
# ============================================================

if st.session_state.running:
    state = step_engine.step(state)
    st.session_state.engine_state = state


if not state.history:
    st.info("Press ▶ Start to begin simulation.")
    st.stop()

tel = state.history[-1]


# ============================================================
# METRICS
# ============================================================

m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("Tick", tel.tick)
m2.metric("Clarity", f"{tel.clarity:.1f}%")
m3.metric("Risk", f"{tel.risk:.1f}%")
m4.metric("Pred Risk", f"{tel.predicted_risk:.1f}%")
m5.metric("State", tel.state.value)
m6.metric("Fusion Conf", f"{tel.fusion_conf*100:.1f}%")

st.markdown("---")


# ============================================================
# VISUAL PANELS
# ============================================================

left, mid, right = st.columns([1.2, 1.0, 1.2])

with left:
    st.subheader("Synthetic IR")

    if state.terrain is None:
        state.terrain = terrain_gen.generate()

    ir = terrain_gen.render_ir(
        state.terrain,
        tel,
        state.ao,
        tel.fusion_conf,
    )

    st.image(ir, use_container_width=True)

with mid:
    st.subheader("Fusion Summary")

    st.write("**Sensor Contributions**")
    if state.fused and state.fused.sensor_contrib:
        df = pd.DataFrame(
            state.fused.sensor_contrib.items(),
            columns=["Sensor", "Weight"],
        ).sort_values("Weight", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No usable measurements.")

    st.write("**Audit Records**")
    st.metric("Audit Chain Length", len(state.audit_chain))

with right:
    st.subheader("Track Map")

    df = pd.DataFrame(
        [{"lat": t.lat, "lon": t.lon} for t in list(state.history)[-100:]]
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position=["lon", "lat"],
                    get_radius=80,
                    get_fill_color=[255, 140, 0, 180],
                )
            ],
            initial_view_state=pdk.ViewState(
                latitude=state.ao.base_lat,
                longitude=state.ao.base_lon,
                zoom=9,
            ),
            map_style="mapbox://styles/mapbox/dark-v10",
        )
    )

st.markdown("---")


# ============================================================
# TELEMETRY TABLE
# ============================================================

st.subheader("Telemetry (Last 40 Ticks)")
df_tel = pd.DataFrame([t.model_dump() for t in list(state.history)[-40:]])
st.dataframe(df_tel, use_container_width=True)


# ============================================================
# AUTO-REFRESH
# ============================================================

if st.session_state.running:
    time.sleep(0.25)
    st.rerun()
