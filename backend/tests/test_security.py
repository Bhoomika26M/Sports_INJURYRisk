import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.database import get_db
from app.models.user import User
from app.models.athlete import Athlete
from app.models.session import Session as UserSession
from app.models.password_otp import PasswordOTP
from app.core.security import get_password_hash, create_access_token
from app.core.otp import hash_otp, PURPOSE_PASSWORD_RECOVERY
from datetime import datetime, timedelta


client = TestClient(app)


# Override database for testing
def get_test_db():
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = get_test_db


@pytest.fixture
def db():
    from app.db.database import SessionLocal, engine, Base
    # Create a fresh database for each test
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up database
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        email=f"test{secrets.token_hex(8)}@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        role="athlete",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db: Session):
    """Create a test admin user."""
    admin = User(
        email=f"admin{secrets.token_hex(8)}@example.com",
        password_hash=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role="administrator",
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_athlete(db: Session, test_user: User):
    """Create a test athlete profile."""
    athlete = Athlete(
        athlete_id="ATH001",
        user_id=test_user.id,
        sport_type="Basketball",
        position="Point Guard",
        age=25,
        height=180.0,
        weight=75.0
    )
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@pytest.fixture
def auth_headers(test_user: User, db: Session):
    """Get authentication headers for test user."""
    token_data = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=30)
    )
    token = token_data["access_token"]
    jti = token_data["jti"]
    expires_at = token_data["expires_at"]
    
    # Create session
    from app.core.security import create_user_session
    create_user_session(db, test_user, jti, expires_at)
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin: User, db: Session):
    """Get authentication headers for admin user."""
    token_data = create_access_token(
        data={"sub": test_admin.email},
        expires_delta=timedelta(minutes=30)
    )
    token = token_data["access_token"]
    jti = token_data["jti"]
    expires_at = token_data["expires_at"]
    
    # Create session
    from app.core.security import create_user_session
    create_user_session(db, test_admin, jti, expires_at)
    
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# TEST: Role Assignment Security
# ============================================================

def test_public_registration_cannot_create_admin(db: Session):
    """Test that public registration cannot create admin accounts."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"malicious{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": "Malicious User",
            "role": "administrator"
        }
    )
    assert response.status_code == 400
    assert "athlete" in response.json()["detail"]


def test_public_registration_forces_athlete_role(db: Session):
    """Test that public registration forces athlete role."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"newuser{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": "New User",
            "role": "athlete"
        }
    )
    assert response.status_code == 201
    user = db.query(User).filter(User.email.like(f"newuser%")).first()
    assert user is not None
    assert user.role == "athlete"


def test_public_registration_cannot_create_coach(db: Session):
    """Test that public registration cannot create coach accounts."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"hacker{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": "Hacker User",
            "role": "coach"
        }
    )
    assert response.status_code == 400


# ============================================================
# TEST: Admin-only user creation
# ============================================================

def test_admin_can_create_professional_role_user(db: Session, admin_headers: dict):
    """An administrator can create a professional-role account."""
    email = f"coach{secrets.token_hex(8)}@example.com"
    response = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "email": email,
            "password": "password123",
            "full_name": "New Coach",
            "role": "coach",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "coach"
    assert "password" not in data and "password_hash" not in data

    created = db.query(User).filter(User.email == email).first()
    assert created is not None
    assert created.role == "coach"


def test_admin_created_user_can_log_in(db: Session, admin_headers: dict):
    """A user created by an admin can authenticate with the given password."""
    email = f"physio{secrets.token_hex(8)}@example.com"
    client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "email": email,
            "password": "password123",
            "full_name": "New Physio",
            "role": "physiotherapist",
        },
    )

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_non_admin_cannot_create_user(db: Session, auth_headers: dict):
    """A regular (athlete) user cannot create users."""
    response = client.post(
        "/api/v1/users/",
        headers=auth_headers,
        json={
            "email": f"sneaky{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": "Sneaky User",
            "role": "administrator",
        },
    )
    assert response.status_code == 403


def test_unauthenticated_cannot_create_user(db: Session):
    """User creation requires authentication."""
    response = client.post(
        "/api/v1/users/",
        json={
            "email": f"anon{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": "Anon User",
            "role": "administrator",
        },
    )
    assert response.status_code == 401


def test_admin_create_user_rejects_duplicate_email(db: Session, admin_headers: dict, test_user: User):
    """Creating a user with an existing email is rejected."""
    response = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "email": test_user.email,
            "password": "password123",
            "full_name": "Duplicate",
            "role": "coach",
        },
    )
    assert response.status_code == 400


def test_admin_create_user_rejects_invalid_role(db: Session, admin_headers: dict):
    """An unknown role is rejected."""
    response = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "email": f"weird{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": "Weird Role",
            "role": "supervillain",
        },
    )
    assert response.status_code == 400


def test_admin_created_athlete_gets_profile(db: Session, admin_headers: dict):
    """An athlete created by an admin still gets an athlete profile."""
    email = f"ath{secrets.token_hex(8)}@example.com"
    response = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "email": email,
            "password": "password123",
            "full_name": "New Athlete",
            "role": "athlete",
            "sport_type": "Soccer",
        },
    )
    assert response.status_code == 201

    created = db.query(User).filter(User.email == email).first()
    profile = db.query(Athlete).filter(Athlete.user_id == created.id).first()
    assert profile is not None
    assert profile.sport_type == "Soccer"


# ============================================================
# TEST: Account Enumeration Protection
# ============================================================

def test_forgot_password_same_response_for_unknown_email(db: Session):
    """Test that forgot password returns same response for unknown email."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": f"nonexistent{secrets.token_hex(8)}@example.com"}
    )
    assert response.status_code == 200
    assert "instructions have been sent" in response.json()["message"]


def test_forgot_password_same_response_for_known_email(db: Session, test_user: User):
    """Test that forgot password returns same response for known email."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user.email}
    )
    assert response.status_code == 200
    assert "instructions have been sent" in response.json()["message"]


# ============================================================
# TEST: Password Security
# ============================================================

def test_password_too_short_rejected(db: Session):
    """Test that passwords shorter than 8 characters are rejected."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "shortpwd@example.com",
            "password": "short",
            "full_name": "Short Password",
            "role": "athlete"
        }
    )
    assert response.status_code == 422


def test_password_validation_on_reset(db: Session, test_user: User):
    """Test that password validation applies to the OTP password reset flow."""
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": test_user.email,
            "otp": "123456",
            "new_password": "short",
        }
    )
    assert response.status_code == 422


# ============================================================
# TEST: IDOR Protection
# ============================================================

def test_athlete_cannot_access_other_athlete(db: Session, test_user: User, test_athlete: Athlete, auth_headers: dict):
    """Test that an athlete cannot access another athlete's profile."""
    # Create another athlete with different user
    other_user = User(
        email="other@example.com",
        password_hash=get_password_hash("password123"),
        full_name="Other User",
        role="athlete",
        is_active=True
    )
    db.add(other_user)
    db.commit()
    
    other_athlete = Athlete(
        athlete_id="ATH002",
        user_id=other_user.id,
        sport_type="Soccer",
        position="Forward",
        age=28,
        height=175.0,
        weight=70.0
    )
    db.add(other_athlete)
    db.commit()
    
    # Try to access other athlete as first user
    response = client.get(f"/api/v1/athletes/{other_athlete.id}", headers=auth_headers)
    assert response.status_code == 403


def test_athlete_cannot_update_other_athlete(db: Session, test_user: User, test_athlete: Athlete, auth_headers: dict):
    """Test that an athlete cannot update another athlete's profile."""
    # Create another athlete
    other_user = User(
        email="other2@example.com",
        password_hash=get_password_hash("password123"),
        full_name="Other User 2",
        role="athlete",
        is_active=True
    )
    db.add(other_user)
    db.commit()
    
    other_athlete = Athlete(
        athlete_id="ATH003",
        user_id=other_user.id,
        sport_type="Tennis",
        position="Server",
        age=30,
        height=185.0,
        weight=80.0
    )
    db.add(other_athlete)
    db.commit()
    
    # Try to update other athlete
    response = client.put(
        f"/api/v1/athletes/{other_athlete.id}",
        json={"age": 31},
        headers=auth_headers
    )
    assert response.status_code == 403


# ============================================================
# TEST: Session Revocation
# ============================================================

def test_logout_revokes_session(db: Session, test_user: User, auth_headers: dict):
    """Test that logout revokes the session."""
    # Logout
    response = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    
    # Try to use the same token again
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 401


def test_revoked_session_cannot_access_protected_endpoint(db: Session, test_user: User, auth_headers: dict):
    """Test that a revoked session cannot access protected endpoints."""
    # Manually revoke session
    sessions = db.query(UserSession).filter(UserSession.user_id == test_user.id).all()
    for session in sessions:
        session.revoked_at = datetime.utcnow()
    db.commit()
    
    # Try to access protected endpoint
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 401


# ============================================================
# TEST: Rate Limiting
# ============================================================

@pytest.mark.skip("Rate limiting tests interfere with other tests")
def test_rate_limiting_on_login(db: Session):
    """Test that login endpoint is rate limited."""
    # Attempt multiple failed logins
    for i in range(15):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"}
        )
    
    # Should be rate limited
    assert response.status_code == 429


@pytest.mark.skip("Rate limiting tests interfere with other tests")
def test_rate_limiting_on_forgot_password(db: Session):
    """Test that forgot password endpoint is rate limited."""
    # Attempt multiple requests
    for i in range(10):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"}
        )
    
    # Should be rate limited
    assert response.status_code == 429


# ============================================================
# TEST: Input Validation
# ============================================================

def test_sql_injection_in_email(db: Session):
    """Test that SQL injection attempts are treated as data."""
    from sqlalchemy import text
    # The email validator accepts the string as a valid email format
    # This is expected - the important thing is it doesn't execute SQL
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "SQL Injection'; DROP TABLE users; --",
            "role": "athlete"
        }
    )
    # Should succeed and store the malicious string as data, not execute it
    assert response.status_code == 201
    
    # Verify the string was stored as data, not executed
    user = db.query(User).filter(User.full_name == "SQL Injection'; DROP TABLE users; --").first()
    assert user is not None
    # Verify table still exists
    tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    table_names = [t[0] for t in tables]
    assert 'users' in table_names


def test_oversized_fields_rejected(db: Session):
    """Test that oversized fields are rejected."""
    long_string = "a" * 200
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"test{secrets.token_hex(8)}@example.com",
            "password": "password123",
            "full_name": long_string,
            "role": "athlete"
        }
    )
    # Should fail validation due to full_name length
    # If rate limited, that's also acceptable
    assert response.status_code in [422, 429]


def test_invalid_email_format(db: Session):
    """Test that invalid email format is rejected."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"invalid{secrets.token_hex(8)}",
            "password": "password123",
            "full_name": "Invalid Email",
            "role": "athlete"
        }
    )
    # Should fail validation or be rate limited
    assert response.status_code in [422, 429]


# ============================================================
# TEST: Authorization
# ============================================================

def test_unauthenticated_request_returns_401(db: Session):
    """Test that unauthenticated requests return 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_unauthorized_role_returns_403(db: Session, test_user: User, auth_headers: dict):
    """Test that unauthorized role returns 403."""
    # Try to access admin-only endpoint as regular user
    response = client.get("/api/v1/users/", headers=auth_headers)
    # Should return 403 (forbidden) not 401 (unauthorized)
    assert response.status_code == 403


def test_athlete_delete_restricted_to_admin(db: Session, test_athlete: Athlete, auth_headers: dict):
    """Test that athlete deletion is restricted to admin."""
    response = client.delete(f"/api/v1/athletes/{test_athlete.id}", headers=auth_headers)
    assert response.status_code == 403


# ============================================================
# TEST: Password Reset Security
# ============================================================

def _issue_recovery_otp_row(db: Session, user: User, code: str, expires_in_minutes: int = 5):
    """Insert a recovery OTP row directly (no email) for endpoint testing."""
    db.add(
        PasswordOTP(
            user_id=user.id,
            purpose=PURPOSE_PASSWORD_RECOVERY,
            otp_hash=hash_otp(code, PURPOSE_PASSWORD_RECOVERY),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
            attempt_count=0,
            max_attempts=5,
        )
    )
    db.commit()


def test_password_reset_otp_single_use(db: Session, test_user: User):
    """Test that a recovery OTP is single-use."""
    code = "123456"
    _issue_recovery_otp_row(db, test_user, code)

    # Use the code once.
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": test_user.email,
            "otp": code,
            "new_password": "newpassword123",
        }
    )
    assert response.status_code == 200

    # The same code cannot be used again.
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": test_user.email,
            "otp": code,
            "new_password": "anotherpassword123",
        }
    )
    assert response.status_code == 400


def test_expired_password_reset_otp_rejected(db: Session, test_user: User):
    """Test that expired recovery OTPs are rejected."""
    code = "654321"
    _issue_recovery_otp_row(db, test_user, code, expires_in_minutes=-1)

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": test_user.email,
            "otp": code,
            "new_password": "newpassword123",
        }
    )
    assert response.status_code == 400


# ============================================================
# TEST: Security Headers
# ============================================================

def test_security_headers_present():
    """Test that security headers are present."""
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


# ============================================================
# TEST: CORS Configuration
# ============================================================

def test_cors_restricted():
    """Test that CORS is restricted to allowed origins."""
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "POST"
        }
    )
    # Should not include malicious origin in access-control-allow-origin
    assert response.headers.get("access-control-allow-origin") != "http://malicious.com"
