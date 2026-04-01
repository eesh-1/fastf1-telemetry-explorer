"""
app.py — FastF1 Telemetry Explorer
Run with:  streamlit run app.py
"""

import streamlit as st
from utils.data_loader import load_session, available_drivers, lap_range
from utils.plots import (
    plot_speed_trace,
    plot_traction_circle,
    plot_lap_overlay,
    plot_gear_map,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="F1 Telemetry Explorer",
    page_icon="🏎️",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f0f1a; }
    section[data-testid="stSidebar"] { background-color: #16213e; }
    h1, h2, h3 { color: #e8002d !important; }
    .stTabs [data-baseweb="tab"] { color: #aaaaaa; }
    .stTabs [aria-selected="true"] { color: #ffffff; border-bottom: 2px solid #e8002d; }
    div[data-testid="stMetric"] { background: #16213e; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏎️  F1 Telemetry Explorer")
st.caption("Powered by FastF1 · Visualised with Plotly")
st.divider()

# ── Sidebar — Session Loader ──────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Session Settings")

    year = st.selectbox("Season", list(range(2024, 2018, -1)), index=0)

    gp_options = [
        "Bahrain", "Saudi Arabia", "Australia", "Japan", "China",
        "Miami", "Emilia Romagna", "Monaco", "Canada", "Spain",
        "Austria", "Great Britain", "Hungary", "Belgium",
        "Netherlands", "Italian", "Azerbaijan", "Singapore",
        "United States", "Mexico", "São Paulo", "Las Vegas", "Abu Dhabi",
    ]
    gp = st.selectbox("Grand Prix", gp_options, index=0)

    session_type = st.selectbox(
        "Session",
        options=["R", "Q", "FP1", "FP2", "FP3", "SQ"],
        format_func=lambda x: {
            "R": "Race", "Q": "Qualifying", "FP1": "Practice 1",
            "FP2": "Practice 2", "FP3": "Practice 3", "SQ": "Sprint Qualifying",
        }[x],
    )

    load_btn = st.button("🚀 Load Session", use_container_width=True)

    if load_btn:
        with st.spinner(f"Loading {gp} {year} — {session_type} …"):
            try:
                session = load_session(year, gp, session_type)
                st.session_state["session"] = session
                st.session_state["gp_label"] = f"{session.event['EventName']} {year}"
                st.success("Session loaded ✔")
            except Exception as e:
                st.error(f"Failed to load session:\n{e}")

    if "gp_label" in st.session_state:
        st.info(f"**Active:** {st.session_state['gp_label']}")

    st.divider()
    st.markdown(
        "**Tip:** First load may take 30–60 s while FastF1 "
        "downloads data. Subsequent loads are instant (cached).",
        unsafe_allow_html=False,
    )

# ── Guard — no session yet ────────────────────────────────────────────────────
if "session" not in st.session_state:
    st.info("👈  Configure a session in the sidebar and click **Load Session** to begin.")
    st.stop()

session = st.session_state["session"]
drivers = available_drivers(session)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_speed, tab_traction, tab_overlay, tab_gear = st.tabs([
    "⚡ Speed Trace",
    "⭕ Traction Circle",
    "📊 Lap Overlay",
    "🗺️  Gear Map",
])

# ─── Tab 1: Speed Trace ───────────────────────────────────────────────────────
with tab_speed:
    st.subheader("Speed Trace + Throttle / Brake")
    st.caption("Speed (km/h) over the lap distance with driver inputs overlaid.")

    col1, col2 = st.columns([1, 3])
    with col1:
        driver_st = st.selectbox("Driver", drivers, key="speed_drv")
        min_lap, max_lap = lap_range(session, driver_st)
        use_fastest_st = st.checkbox("Use fastest lap", value=True, key="speed_fastest")
        if not use_fastest_st:
            lap_num_st = st.slider("Lap number", min_lap, max_lap, min_lap, key="speed_lap")
        else:
            lap_num_st = None
        go_st = st.button("Plot", key="go_speed", use_container_width=True)

    with col2:
        if go_st or "speed_fig" in st.session_state:
            try:
                with st.spinner("Rendering …"):
                    fig = plot_speed_trace(session, driver_st, lap_num_st)
                    st.session_state["speed_fig"] = fig
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(str(e))

# ─── Tab 2: Traction Circle ───────────────────────────────────────────────────
with tab_traction:
    st.subheader("Traction Circle (G-Force)")
    st.caption(
        "Lateral vs longitudinal G-force. A driver using the full tyre envelope "
        "fills the circle. Colours indicate speed."
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        driver_tc = st.selectbox("Driver", drivers, key="tc_drv")
        min_lap, max_lap = lap_range(session, driver_tc)
        use_fastest_tc = st.checkbox("Use fastest lap", value=True, key="tc_fastest")
        if not use_fastest_tc:
            lap_num_tc = st.slider("Lap number", min_lap, max_lap, min_lap, key="tc_lap")
        else:
            lap_num_tc = None
        go_tc = st.button("Plot", key="go_tc", use_container_width=True)

    with col2:
        if go_tc:
            try:
                with st.spinner("Computing G-forces …"):
                    fig = plot_traction_circle(session, driver_tc, lap_num_tc)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(str(e))

# ─── Tab 3: Lap Overlay ───────────────────────────────────────────────────────
with tab_overlay:
    st.subheader("Lap Overlay Comparison")
    st.caption(
        "Compare any telemetry channel across multiple drivers. "
        "When two drivers are selected on Speed, a Δ Speed line is added."
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        selected_drivers = st.multiselect(
            "Drivers to compare", drivers,
            default=drivers[:2] if len(drivers) >= 2 else drivers,
            key="ov_drivers",
        )
        channel = st.selectbox(
            "Channel",
            ["Speed", "Throttle", "Brake", "RPM", "nGear"],
            key="ov_channel",
        )
        st.markdown("**Lap selection (leave 0 = fastest)**")
        lap_inputs = {}
        for d in selected_drivers:
            min_l, max_l = lap_range(session, d)
            n = st.number_input(
                f"{d}", min_value=0, max_value=max_l,
                value=0, key=f"ov_lap_{d}",
                help="0 = fastest lap",
            )
            lap_inputs[d] = None if n == 0 else int(n)
        go_ov = st.button("Plot", key="go_ov", use_container_width=True)

    with col2:
        if go_ov:
            if len(selected_drivers) < 1:
                st.warning("Select at least one driver.")
            else:
                try:
                    with st.spinner("Overlaying laps …"):
                        lap_nums = [lap_inputs[d] for d in selected_drivers]
                        fig = plot_lap_overlay(
                            session, selected_drivers, lap_nums, channel
                        )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(str(e))

# ─── Tab 4: Gear Map ─────────────────────────────────────────────────────────
with tab_gear:
    st.subheader("Circuit Gear Map")
    st.caption(
        "Track layout coloured by the gear the driver is using at each point. "
        "Reveals braking zones and acceleration phases visually."
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        driver_gm = st.selectbox("Driver", drivers, key="gm_drv")
        min_lap, max_lap = lap_range(session, driver_gm)
        use_fastest_gm = st.checkbox("Use fastest lap", value=True, key="gm_fastest")
        if not use_fastest_gm:
            lap_num_gm = st.slider("Lap number", min_lap, max_lap, min_lap, key="gm_lap")
        else:
            lap_num_gm = None
        go_gm = st.button("Plot", key="go_gm", use_container_width=True)

    with col2:
        if go_gm:
            try:
                with st.spinner("Drawing track map …"):
                    fig = plot_gear_map(session, driver_gm, lap_num_gm)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(str(e))
