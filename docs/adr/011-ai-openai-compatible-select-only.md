# ADR-011 — AI: provider-agnostic, OpenAI-compatible, SELECT-only over DuckDB

**Status:** Accepted (Phase 5)

## Decision
A provider-agnostic, OpenAI-compatible client behind a confirmed-later Qwen3-class endpoint
(vLLM/SGLang). The AI may only run **SELECT** over DuckDB, via a dedicated read-only connection,
with sqlglot SELECT-only validation + schema allow-list + row/time caps. Scoped schema injection
(only the user's accessible tables) + `describe_table` on demand — never a whole-catalog dump.

## Why
The exact model/endpoint is unconfirmed; designing to capabilities (tool calling, OpenAI-compatible
API) keeps the build swappable. Oracle credentials and the write path are never reachable from chat.

## Status note
`/api/ai/*` ships the scaffold + the SELECT-only guard (`upm_sql_tools.validate`). The tool-calling
loop (`list_tables`/`describe_table`/`run_readonly_sql`/`propose_chart`) lands once the endpoint is
confirmed.
