import asyncio
import os
import sys
import hashlib
from sqlalchemy import select

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.enums import UserRole


def hash_password(password: str) -> str:
    """Hash password using bcrypt if available, else standard SHA-256 with salt."""
    try:
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except ImportError:
        # Fallback hash if bcrypt binary is not pre-installed
        salt = "sports_injury_risk_salt"
        return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()


async def seed_admin():
    admin_email = os.getenv("ADMIN_SEED_EMAIL", "admin@kinetirisk.com").lower().strip()
    admin_password = os.getenv("ADMIN_SEED_PASSWORD", "Admin@12345")
    admin_name = os.getenv("ADMIN_SEED_NAME", "System Administrator")

    print(f"Connecting to database to verify/seed admin user '{admin_email}'...")

    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        query = select(User).where(User.email == admin_email)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"[INFO] Admin user '{admin_email}' already exists (ID: {existing_user.id}). Skipping creation.")
            return

        # Create new admin user
        hashed_pw = hash_password(admin_password)
        new_admin = User(
            email=admin_email,
            hashed_password=hashed_pw,
            full_name=admin_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )

        session.add(new_admin)
        await session.commit()
        await session.refresh(new_admin)

        print("\n========================================================")
        print("  Admin User Seeded Successfully!")
        print("========================================================")
        print(f"  User ID:    {new_admin.id}")
        print(f"  Full Name:  {new_admin.full_name}")
        print(f"  Email:      {new_admin.email}")
        print(f"  Role:       {new_admin.role.value}")
        print(f"  Password:   {admin_password}")
        print(f"  Active:     {new_admin.is_active}")
        print(f"  Verified:   {new_admin.is_verified}")
        print("========================================================\n")


if __name__ == "__main__":
    asyncio.run(seed_admin())
