# ADR-010 — Maps: MapLibre GL (production) + Kepler.gl (exploration)

**Status:** Accepted (Phase 4)

## Decision
MapLibre GL for production map widgets; Kepler.gl for ad-hoc exploration. Geospatial queries run
on the DuckDB `spatial` backend (site lat/long).

## Why
Open-source, on-prem-friendly, no cloud tiles required; DuckDB `spatial` keeps geo queries in the
same engine as the KPIs.

## Status note
Map widget type is reserved in the dashboard schema (`viz: { lat, lon, weight, tooltip[] }`);
rendering lands in Phase 4.
