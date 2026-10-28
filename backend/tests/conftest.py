import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

# 1. Create SQLite in-memory engine
engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Patch the app modules before tests run
import app.db.session
app.db.session.engine = engine
app.db.session.SessionLocal = TestingSessionLocal

from app.api.deps import get_db
from app.main import app

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    from app.db.session import Base
    import app.models.user
    import app.models.athlete
    import app.models.assignment
    import app.models.video
    
    print("REGISTERED TABLES:", Base.metadata.tables.keys())
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_user(db_session):
    from app.models.user import User
    from app.core.security import get_password_hash
    import uuid
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test Athlete",
        role="athlete",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
