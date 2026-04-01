# FastF1-Telemetry-Explorer
🏎️ Interactive F1 telemetry dashboard built with FastF1 &amp; Streamlit — speed traces, traction circles, lap overlays and gear maps from real race data.
# 🏎️ FastF1 Telemetry Explorer

An interactive web dashboard to explore real Formula 1 telemetry data 
pulled directly from official F1 timing systems via the FastF1 API.

## What it does
- 📡 Fetches real lap-by-lap telemetry for any driver, session, and Grand Prix from 2019–2024
- ⚡ Speed Trace — visualises speed, throttle and brake inputs over a lap
- ⭕ Traction Circle — plots lateral vs longitudinal G-forces computed from raw position data
- 📊 Lap Overlay — compares any two drivers' telemetry on the same chart with a delta line
- 🗺️ Gear Map — renders the full circuit layout coloured by gear engaged at each point

## Tech Stack
Python · FastF1 · Streamlit · Plotly · Pandas · NumPy

## Why I built this
Part of my motorsport engineering portfolio. Real F1 teams use telemetry 
analysis as a core part of race strategy and car setup — this project 
demonstrates data literacy with actual racing data.
