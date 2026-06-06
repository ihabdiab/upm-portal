# ADR-008 — RBAC as capabilities, project-scoped

**Status:** Accepted

## Decision
Roles map to **capability sets** (`user:manage`, `job:author`, `dashboard:author`,
`project:view`); access is scoped per project. Three roles ship (Admin / Builder / Viewer);
Admin is global.

## Why
Splitting e.g. "Job Author" from "Dashboard Author" later becomes a config change (add a role
row), not a code refactor.

## Trade-off
Slightly more indirection than hardcoded roles. Worth it.

## Implementation
`capabilities`, `roles`, `role_capabilities`, `user_project_roles` tables; checks in
`upm_backend/deps.py` (`require_cap`, `ensure_project_view`).
