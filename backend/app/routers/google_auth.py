"""
Google OAuth2 routes using Authlib.

Flow
────
1. GET /auth/google/login
   → Generates a PKCE / state-protected redirect URL to Google's consent screen.
   → Stores the state in a signed cookie so the callback can verify it.

2. GET /auth/google/callback?code=...&state=...
   → Exchanges the code for tokens, fetches the Google userinfo.
   → Creates the user (athlete role) if not seen before, OR links the
     google_id to an existing email-matched account.
   → Issues our own JWT pair and redirects the browser to
     FRONTEND_URL/auth/callback?access_token=...&refresh_token=...
     so the React app can pick them up from the query string.

Environment variables required
───────────────────────────────
  GOOGLE_CLIENT_ID      – from Google Cloud Console
  GOOGLE_CLIENT_SECRET  – from Google Cloud Console
  GOOGLE_REDIRECT_URI   – must match the Authorized Redirect URI in GCP
                          (default: http://localhost:8000/api/v1/auth/google/callback)
  FRONTEND_URL          – where to redirect after success (default: http://localhost:5173)
"""
import secrets
import urllib.parse

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.deps import get_db
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication – Google OAuth2"])

# ── Constants ────────────────────────────────────────────────────────────────
GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES       = "openid email profile"

# Cookie name that carries the signed OAuth state
_STATE_COOKIE = "google_oauth_state"
# State signature is valid for 10 minutes
_STATE_MAX_AGE = 600

# Signer – uses the app SECRET_KEY so forged cookies are rejected
_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="google-oauth-state")


# ── Helpers ──────────────────────────────────────────────────────────────────
def _oauth_client() -> AsyncOAuth2Client:
    """Return a fresh Authlib async OAuth2 client configured for Google."""
    return AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        scope=GOOGLE_SCOPES,
    )


def _check_configured() -> None:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google OAuth2 is not configured. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment."
            ),
        )


# ── GET /auth/google/login ────────────────────────────────────────────────────
@router.get(
    "/google/login",
    summary="Initiate Google OAuth2 login flow",
    description=(
        "Redirects the browser to Google's consent screen. "
        "A signed `state` token is stored in an HttpOnly cookie to prevent CSRF."
    ),
    status_code=status.HTTP_302_FOUND,
)
async def google_login() -> RedirectResponse:
    _check_configured()

    state = secrets.token_urlsafe(32)
    signed_state = _signer.dumps(state)

    client = _oauth_client()
    # Build the Google authorisation URL
    auth_url, _ = client.create_authorization_url(
        GOOGLE_AUTH_URL,
        state=state,
        access_type="offline",   # request refresh_token from Google
        prompt="select_account", # always show account picker
    )

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    # Store the signed state in an HttpOnly SameSite=Lax cookie
    response.set_cookie(
        key=_STATE_COOKIE,
        value=signed_state,
        httponly=True,
        samesite="lax",
        secure=False,  # set to True in production (HTTPS)
        max_age=_STATE_MAX_AGE,
    )
    return response


# ── GET /auth/google/callback ─────────────────────────────────────────────────
@router.get(
    "/google/callback",
    summary="Google OAuth2 callback",
    description=(
        "Google redirects here after the user approves (or denies) access. "
        "On success, creates/links the user and redirects to the frontend "
        "with our own JWT tokens in the query string."
    ),
    status_code=status.HTTP_302_FOUND,
)
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    _check_configured()

    # ── 1. Validate state ────────────────────────────────────────────────────
    state_from_google = request.query_params.get("state")
    signed_state      = request.cookies.get(_STATE_COOKIE)
    error_param       = request.query_params.get("error")

    # User denied the Google consent screen
    if error_param:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=google_denied",
            status_code=status.HTTP_302_FOUND,
        )

    if not signed_state or not state_from_google:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=missing_state",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        expected_state = _signer.loads(signed_state, max_age=_STATE_MAX_AGE)
    except (SignatureExpired, BadSignature):
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=invalid_state",
            status_code=status.HTTP_302_FOUND,
        )

    if expected_state != state_from_google:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=state_mismatch",
            status_code=status.HTTP_302_FOUND,
        )

    # ── 2. Exchange authorisation code for tokens ────────────────────────────
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=no_code",
            status_code=status.HTTP_302_FOUND,
        )

    client = _oauth_client()
    try:
        token_data = await client.fetch_token(
            GOOGLE_TOKEN_URL,
            code=code,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
    except Exception:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=token_exchange_failed",
            status_code=status.HTTP_302_FOUND,
        )

    # ── 3. Fetch Google user profile ─────────────────────────────────────────
    try:
        resp = await client.get(GOOGLE_USERINFO_URL)
        resp.raise_for_status()
        userinfo: dict = resp.json()
    except Exception:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=userinfo_failed",
            status_code=status.HTTP_302_FOUND,
        )

    google_id:  str       = userinfo["sub"]
    email:      str       = userinfo.get("email", "").lower()
    full_name:  str       = userinfo.get("name", email.split("@")[0])
    avatar_url: str | None = userinfo.get("picture")
    email_verified: bool  = userinfo.get("email_verified", False)

    if not email:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=no_email",
            status_code=status.HTTP_302_FOUND,
        )

    # ── 4. Find or create the user ───────────────────────────────────────────
    # Priority: lookup by google_id first, then by email (link account)
    result = await db.execute(select(User).where(User.google_id == google_id))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        # Try to link to an existing email account
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            # Brand-new user – create with athlete role
            user = User(
                email=email,
                hashed_password=None,       # OAuth users have no password
                full_name=full_name,
                role=UserRole.ATHLETE,
                is_active=True,
                is_verified=email_verified,
                google_id=google_id,
                avatar_url=avatar_url,
            )
            db.add(user)
            await db.flush()
        else:
            # Existing email account – link Google identity
            user.google_id  = google_id
            user.avatar_url = avatar_url or user.avatar_url
            if email_verified and not user.is_verified:
                user.is_verified = True
    else:
        # Known Google user – refresh avatar if changed
        if avatar_url:
            user.avatar_url = avatar_url

    if not user.is_active:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=account_deactivated",
            status_code=status.HTTP_302_FOUND,
        )

    await db.flush()
    await db.refresh(user)

    # ── 5. Issue our own JWT pair ────────────────────────────────────────────
    access_token  = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    # ── 6. Redirect to frontend with tokens in query string ──────────────────
    params = urllib.parse.urlencode({
        "access_token":  access_token,
        "refresh_token": refresh_token,
    })
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?{params}"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    # Clear the state cookie
    response.delete_cookie(_STATE_COOKIE)
    return response
