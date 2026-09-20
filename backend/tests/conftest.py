import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
        "role": "athlete"
    }


@pytest.fixture
def admin_user_data():
    return {
        "email": "admin@example.com",
        "password": "adminpass123",
        "full_name": "Admin User",
        "role": "administrator"
    }


@pytest.fixture
def test_athlete_data():
    return {
        "athlete_id": "ATH001",
        "sport_type": "Basketball",
        "position": "Point Guard",
        "age": 25,
        "height": 180.5,
        "weight": 75.0,
        "injury_history": "None",
        "training_load": "Moderate"
    }
