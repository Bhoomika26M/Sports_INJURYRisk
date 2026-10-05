from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def test_connection():
    try:
        with engine.connect() as connection:
            print("✅ Database connection successful!")
    except Exception as e:
        print("❌ Database connection failed:", e)

def create_tables():
    Base.metadata.create_all(bind=engine)