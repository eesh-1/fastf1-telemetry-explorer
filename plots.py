"""
plots.py — Plotly visualization functions for F1 telemetry.

Functions:
  plot_speed_trace      — Speed + throttle/brake vs distance
  plot_traction_circle  — Lateral vs longitudinal G-force scatter
  plot_lap_overlay      — Side-by-side speed traces of multiple drivers
  plot_gear_map         — Circuit map coloured by gear
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Colour palette ────────────────────────────────────────────────────────────
BG_DARK  = "#0f0f1a"
BG_PANEL = "#16213e"
RED      = "#e8002d"
GREEN    = "#00d2be"
YELLOW   = "#ffd700"
WHITE    = "#f0f0f0"
GREY     = "#888888"

DRIVER_COLOURS = [
    "#e8002d", "#00d2be", "#ffd700", "#ff8700",
    "#0600ef", "#ffffff", "#15e6cd", "#b6babd",
]

GEAR_COLOURS = {
    1: "#2b0fff", 2: "#0070ff", 3: "#00cfdd",
    4: "#00ff87", 5: "#ffd700", 6: "#ff8700",
    7: "#ff4444", 8: "#ff0066",
}


def _layout_defaults(fig, title: str, height: int = 460):
    fig.update_layout(
        title=dict(text=title, font=dict(color=WHITE, size=17)),
        paper_bgcolor=BG_DARK,
        plot_bgcolor=BG_PANEL,
        font=dict(color=WHITE, family="monospace"),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=GREY),
        height=height,
        margin=dict(t=60, b=50, l=60, r=40),
    )
    fig.update_xaxes(gridcolor="#2a2a3e", zerolinecolor="#2a2a3e")
    fig.update_yaxes(gridcolor="#2a2a3e", zerolinecolor="#2a2a3e")
    return fig


# ── 1. Speed Trace ────────────────────────────────────────────────────────────
def plot_speed_trace(session, driver: str, lap_number: int | None = None) -> go.Figure:
    """Speed (km/h) and throttle/brake traces vs distance for one lap."""
    from utils.data_loader import get_driver_lap

    lap = get_driver_lap(session, driver, lap_number)
    if lap is None:
        raise ValueError(f"No lap found for {driver} #{lap_number}")

    tel = lap.get_telemetry().add_distance()
    lap_label = f"Lap {int(lap['LapNumber'])}"

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.04,
    )

    # Speed
    fig.add_trace(go.Scatter(
        x=tel["Distance"], y=tel["Speed"],
        mode="lines", name="Speed (km/h)",
        line=dict(color=RED, width=2),
    ), row=1, col=1)

    # Throttle
    fig.add_trace(go.Scatter(
        x=tel["Distance"], y=tel["Throttle"],
        mode="lines", name="Throttle %",
        line=dict(color=GREEN, width=1.5),
        fill="tozeroy", fillcolor="rgba(0,210,190,0.12)",
    ), row=2, col=1)

    # Brake (binary 0/1 → 0/100 for visibility)
    brake_pct = tel["Brake"].astype(float) * 100
    fig.add_trace(go.Scatter(
        x=tel["Distance"], y=brake_pct,
        mode="lines", name="Brake",
        line=dict(color=YELLOW, width=1.5),
        fill="tozeroy", fillcolor="rgba(255,215,0,0.12)",
    ), row=2, col=1)

    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    fig.update_yaxes(title_text="Input %", range=[0, 105], row=2, col=1)
    fig.update_xaxes(title_text="Distance (m)", row=2, col=1)

    _layout_defaults(fig, f"Speed Trace — {driver}  ·  {lap_label}", height=520)
    return fig


# ── 2. Traction Circle ────────────────────────────────────────────────────────
def _compute_g_forces(tel: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute lateral and longitudinal G-forces from telemetry.
    Uses speed (m/s) time-derivatives and XY path curvature.
    """
    g = 9.81

    # Convert speed to m/s
    speed_ms = tel["Speed"].to_numpy() / 3.6

    # Time in seconds
    time_s = tel["Time"].dt.total_seconds().to_numpy()
    dt = np.diff(time_s, prepend=time_s[0])
    dt[dt == 0] = 1e-6  # avoid division by zero

    # Longitudinal G = dv/dt / g
    dv = np.diff(speed_ms, prepend=speed_ms[0])
    long_g = dv / dt / g

    # Lateral G = v² * κ / g   (κ = curvature of XY path)
    x = tel["X"].to_numpy()
    y = tel["Y"].to_numpy()
    dx = np.gradient(x, time_s)
    dy = np.gradient(y, time_s)
    ddx = np.gradient(dx, time_s)
    ddy = np.gradient(dy, time_s)
    denom = (dx**2 + dy**2) ** 1.5
    denom[denom < 1e-6] = 1e-6
    kappa = (dx * ddy - dy * ddx) / denom
    lat_g = speed_ms**2 * kappa / g

    # Smooth with rolling window to reduce sensor noise
    def smooth(arr, w=5):
        return pd.Series(arr).rolling(w, center=True, min_periods=1).mean().to_numpy()

    return smooth(lat_g), smooth(long_g)


def plot_traction_circle(session, driver: str, lap_number: int | None = None) -> go.Figure:
    """Lateral vs longitudinal G-force — the classic traction circle."""
    from utils.data_loader import get_driver_lap

    lap = get_driver_lap(session, driver, lap_number)
    if lap is None:
        raise ValueError(f"No lap found for {driver} #{lap_number}")

    tel = lap.get_telemetry()
    lat_g, long_g = _compute_g_forces(tel)

    # Colour points by speed for extra info density
    speed = tel["Speed"].to_numpy()

    fig = go.Figure()

    # Draw unit circles at 1G, 2G, 3G for reference
    theta = np.linspace(0, 2 * np.pi, 200)
    for r, opacity in [(1, 0.25), (2, 0.15), (3, 0.08)]:
        fig.add_trace(go.Scatter(
            x=r * np.cos(theta), y=r * np.sin(theta),
            mode="lines",
            line=dict(color=GREY, width=1, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(x=r * 0.72, y=r * 0.72,
                           text=f"{r}G", showarrow=False,
                           font=dict(color=GREY, size=10))

    # Scatter coloured by speed
    fig.add_trace(go.Scatter(
        x=lat_g, y=long_g,
        mode="markers",
        name=f"{driver}",
        marker=dict(
            color=speed,
            colorscale="Turbo",
            size=3,
            colorbar=dict(title="Speed<br>(km/h)", thickness=12),
            opacity=0.85,
        ),
    ))

    # Axis lines
    for x0, y0, x1, y1 in [(-3.5, 0, 3.5, 0), (0, -3.5, 0, 3.5)]:
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(color=GREY, width=1))

    fig.update_xaxes(title_text="Lateral G  (← Left  |  Right →)",
                     range=[-3.5, 3.5], zeroline=False)
    fig.update_yaxes(title_text="Longitudinal G  (↓ Brake  |  Accel ↑)",
                     range=[-3.5, 3.5], zeroline=False, scaleanchor="x")

    _layout_defaults(fig, f"Traction Circle — {driver}  ·  Lap {int(lap['LapNumber'])}")
    return fig


# ── 3. Lap Overlay Comparison ─────────────────────────────────────────────────
def plot_lap_overlay(
    session,
    drivers: list[str],
    lap_numbers: list[int | None] | None = None,
    channel: str = "Speed",
) -> go.Figure:
    """
    Overlay a telemetry channel (Speed, Throttle, RPM, etc.)
    for multiple drivers on the same distance axis.
    """
    from utils.data_loader import get_driver_lap

    if lap_numbers is None:
        lap_numbers = [None] * len(drivers)

    fig = go.Figure()

    for i, (driver, lap_num) in enumerate(zip(drivers, lap_numbers)):
        lap = get_driver_lap(session, driver, lap_num)
        if lap is None:
            continue
        tel = lap.get_telemetry().add_distance()
        colour = DRIVER_COLOURS[i % len(DRIVER_COLOURS)]
        label = f"{driver}  Lap {int(lap['LapNumber'])}"

        fig.add_trace(go.Scatter(
            x=tel["Distance"], y=tel[channel],
            mode="lines", name=label,
            line=dict(color=colour, width=2),
        ))

    # Delta line (only for exactly 2 drivers, Speed channel)
    if len(drivers) == 2 and channel == "Speed":
        laps = [get_driver_lap(session, d, n)
                for d, n in zip(drivers, lap_numbers)]
        if all(l is not None for l in laps):
            tel0 = laps[0].get_telemetry().add_distance()
            tel1 = laps[1].get_telemetry().add_distance()
            # Interpolate onto common distance grid
            dist_common = np.linspace(
                max(tel0["Distance"].min(), tel1["Distance"].min()),
                min(tel0["Distance"].max(), tel1["Distance"].max()),
                500,
            )
            spd0 = np.interp(dist_common, tel0["Distance"], tel0["Speed"])
            spd1 = np.interp(dist_common, tel1["Distance"], tel1["Speed"])
            delta = spd0 - spd1

            fig.add_trace(go.Scatter(
                x=dist_common, y=delta,
                mode="lines", name=f"Δ Speed ({drivers[0]}−{drivers[1]})",
                line=dict(color=WHITE, width=1.5, dash="dot"),
                yaxis="y2",
            ))
            fig.update_layout(
                yaxis2=dict(
                    title="Δ Speed (km/h)", overlaying="y",
                    side="right", zeroline=True,
                    zerolinecolor=GREY, zerolinewidth=1,
                )
            )

    channel_units = {
        "Speed": "km/h", "Throttle": "%", "Brake": "on/off",
        "RPM": "RPM", "nGear": "Gear",
    }
    unit = channel_units.get(channel, "")
    fig.update_xaxes(title_text="Distance (m)")
    fig.update_yaxes(title_text=f"{channel} ({unit})")

    _layout_defaults(fig, f"Lap Overlay — {channel}  ·  {' vs '.join(drivers)}")
    return fig


# ── 4. Gear Map ───────────────────────────────────────────────────────────────
def plot_gear_map(session, driver: str, lap_number: int | None = None) -> go.Figure:
    """Circuit map coloured by gear engaged."""
    from utils.data_loader import get_driver_lap

    lap = get_driver_lap(session, driver, lap_number)
    if lap is None:
        raise ValueError(f"No lap found for {driver} #{lap_number}")

    tel = lap.get_telemetry().add_distance()
    tel = tel.dropna(subset=["X", "Y", "nGear"])
    tel["nGear"] = tel["nGear"].astype(int)

    fig = go.Figure()

    # Draw one trace per gear so legend is clean
    for gear in sorted(tel["nGear"].unique()):
        subset = tel[tel["nGear"] == gear]
        colour = GEAR_COLOURS.get(gear, WHITE)
        fig.add_trace(go.Scatter(
            x=subset["X"], y=subset["Y"],
            mode="markers",
            name=f"Gear {gear}",
            marker=dict(color=colour, size=4, opacity=0.9),
        ))

    fig.update_xaxes(title_text="", showticklabels=False, showgrid=False)
    fig.update_yaxes(title_text="", showticklabels=False, showgrid=False,
                     scaleanchor="x")

    _layout_defaults(fig, f"Gear Map — {driver}  ·  Lap {int(lap['LapNumber'])}", height=520)
    fig.update_layout(plot_bgcolor=BG_DARK)
    return fig
