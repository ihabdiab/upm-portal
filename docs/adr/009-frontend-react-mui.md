# ADR-009 — Frontend: React + Vite + MUI v6 (Material-3 theming)

**Status:** Accepted

## Decision
React + Vite + MUI v6 with Material-3 color-role theming. `@material/web` (official M3 web
components) is the strict-fidelity fallback if pixel-exact M3 is mandated.

## Why
Pragmatic, mature React path; fast dev server; rich component set; charts via Recharts; maps via
MapLibre later. Decided now to avoid churn.

## Trade-off / revisit
MUI's M3 theming is "M3-flavored", not pixel-exact. Switch to `@material/web` only if exact M3
fidelity becomes a hard requirement.
