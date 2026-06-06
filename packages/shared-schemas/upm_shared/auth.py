"""Auth + identity contracts (§6)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserOut | None = None


class ProjectMembership(BaseModel):
    project_id: int
    project_name: str
    role: str


class MeResponse(BaseModel):
    user: UserOut
    capabilities: list[str]
    projects: list[ProjectMembership]
