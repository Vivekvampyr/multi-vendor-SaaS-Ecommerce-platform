"""
Convenient CLI script to create or promote a Platform Admin user.
Usage:
    python create_admin.py --email admin@example.com --password AdminPassword123! --name "Platform Admin"
Or interactively:
    python create_admin.py
"""

import argparse
import sys
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository


def create_or_promote_admin(email: str, password: str = None, full_name: str = "Platform Admin"):
    email = email.strip().lower()
    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        existing = user_repo.get_by_email(email)

        if existing:
            existing.role = UserRole.ADMIN
            existing.is_active = True
            if password:
                existing.hashed_password = hash_password(password)
            if full_name:
                existing.full_name = full_name
            db.commit()
            print(f"✅ Successfully promoted existing user '{email}' to ADMIN!")
        else:
            if not password:
                print("❌ Error: Password is required for creating a new user.")
                sys.exit(1)

            admin_user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"✅ Successfully created new ADMIN account for '{email}'!")

        print("\n🚀 You can now log in at: http://localhost:8000/login")
        print("🔗 Admin Dashboard URL: http://localhost:8000/admin/dashboard\n")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote an Admin user.")
    parser.add_argument("--email", type=str, help="Admin email address")
    parser.add_argument("--password", type=str, help="Admin password")
    parser.add_argument("--name", type=str, default="Platform Admin", help="Admin display name")

    args = parser.parse_args()

    email = args.email or input("Enter Admin Email: ").strip()
    password = args.password
    if not password and not args.email:
        import getpass
        password = getpass.getpass("Enter Admin Password: ").strip()

    name = args.name or "Platform Admin"

    create_or_promote_admin(email=email, password=password, full_name=name)
