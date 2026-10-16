"""Auth cookie helpers — one place that decides how auth cookies are issued.

Refresh token: httpOnly, Secure (config), SameSite=Lax, scoped to the auth routes. Never exposed to
JavaScript and never stored by the frontend. OAuth state: same attributes, short-lived.
"""

from fastapi import Response

from app.config import settings

REFRESH_COOKIE = "refresh_token"
OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_ROLE_COOKIE = "oauth_role"
AUTH_COOKIE_PATH = "/api/v1/auth"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60
OAUTH_STATE_MAX_AGE = 10 * 60


def _set(response: Response, key: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=key, value=value, max_age=max_age, path=AUTH_COOKIE_PATH,
        httponly=True, secure=settings.cookie_secure, samesite="lax",
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    _set(response, REFRESH_COOKIE, token, REFRESH_COOKIE_MAX_AGE)


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path=AUTH_COOKIE_PATH)


def set_oauth_state_cookie(response: Response, state: str) -> None:
    _set(response, OAUTH_STATE_COOKIE, state, OAUTH_STATE_MAX_AGE)


def clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path=AUTH_COOKIE_PATH)


def set_oauth_role_cookie(response: Response, role: str) -> None:
    _set(response, OAUTH_ROLE_COOKIE, role, OAUTH_STATE_MAX_AGE)


def clear_oauth_role_cookie(response: Response) -> None:
    response.delete_cookie(key=OAUTH_ROLE_COOKIE, path=AUTH_COOKIE_PATH)


SESSION_HINT_COOKIE = "session_hint"


def set_session_hint_cookie(response: Response) -> None:
    response.set_cookie(
        key=SESSION_HINT_COOKIE, value="1", max_age=REFRESH_COOKIE_MAX_AGE, path="/",
        httponly=False, secure=settings.cookie_secure, samesite="lax",
    )


def clear_session_hint_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_HINT_COOKIE, path="/")


