import os
import fastf1
import streamlit as st

# Create cache directory if it doesn't exist
os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")


@st.cache_resource(show_spinner=False)
def load_session(year: int, gp: str, session_type: str):
    """Load a FastF1 session and cache it so repeated calls don't re-fetch."""
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=True, weather=False, messages=False)
    return session


def get_driver_lap(session, driver: str, lap_number: int | None = None):
    laps = session.laps.pick_driver(driver)
    if lap_number is None:
        return laps.pick_fastest()
    matches = laps[laps["LapNumber"] == lap_number]
    if matches.empty:
        return None
    return matches.iloc[0]


def available_drivers(session) -> list[str]:
    return sorted(session.laps["Driver"].dropna().unique().tolist())


def lap_range(session, driver: str) -> tuple[int, int]:
    laps = session.laps.pick_driver(driver)
    return int(laps["LapNumber"].min()), int(laps["LapNumber"].max())
