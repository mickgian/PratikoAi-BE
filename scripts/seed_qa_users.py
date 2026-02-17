#!/usr/bin/env python3
r"""Seed QA environment with standardized test accounts.

Creates dedicated test users for QA environment testing:
- admin@pratiko.app (admin role)
- super@pratiko.app (super_user role)
- user@pratiko.app (regular_user role)

Usage:
    # Against QA database (via Docker Compose)
    docker compose exec app /app/.venv/bin/python scripts/seed_qa_users.py

    # Against local database
    POSTGRES_URL=postgresql://aifinance:devpass@localhost:5433/aifinance \  # pragma: allowlist secret
        uv run python scripts/seed_qa_users.py
"""

import os
import sys

import bcrypt
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://aifinance:devpass@localhost:5433/aifinance",  # pragma: allowlist secret
)

# QA test accounts with known passwords for testing
QA_USERS = [
    {
        "email": "admin@pratiko.app",
        "name": "QA Admin",
        "role": "admin",
        "password": "QaAdmin2026!",  # pragma: allowlist secret
        "account_code": "QA-ADMIN",
        "billing_plan_slug": "premium",
    },
    {
        "email": "super@pratiko.app",
        "name": "QA Super User",
        "role": "super_user",
        "password": "QaSuper2026!",  # pragma: allowlist secret
        "account_code": "QA-SUPER",
        "billing_plan_slug": "pro",
    },
    {
        "email": "user@pratiko.app",
        "name": "QA Basic User",
        "role": "regular_user",
        "password": "QaUser2026!",  # pragma: allowlist secret
        "account_code": "QA-USER",
        "billing_plan_slug": "base",
    },
]


def hash_password(password: str) -> str:
    """Hash password using bcrypt (matches app.models.user.User pattern)."""
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def seed_qa_users() -> None:
    """Insert or update QA test users."""
    engine = create_engine(DATABASE_URL)

    print(f"Seeding QA users to: {DATABASE_URL.split('@')[-1]}")
    print()

    with engine.connect() as conn:
        for user in QA_USERS:
            hashed = hash_password(user["password"])

            # Upsert: insert or update on email conflict
            result = conn.execute(
                text("""
                    INSERT INTO "user" (email, name, role, hashed_password, provider, account_code, billing_plan_slug)
                    VALUES (:email, :name, :role, :hashed_password, 'email', :account_code, :billing_plan_slug)
                    ON CONFLICT (email) DO UPDATE SET
                        name = EXCLUDED.name,
                        role = EXCLUDED.role,
                        hashed_password = EXCLUDED.hashed_password,
                        account_code = EXCLUDED.account_code,
                        billing_plan_slug = EXCLUDED.billing_plan_slug
                    RETURNING id
                """),
                {
                    "email": user["email"],
                    "name": user["name"],
                    "role": user["role"],
                    "hashed_password": hashed,
                    "account_code": user["account_code"],
                    "billing_plan_slug": user["billing_plan_slug"],
                },
            )
            user_id = result.fetchone()[0]
            print(f"  {user['role']:15} | {user['email']:25} | id={user_id} | plan={user['billing_plan_slug']}")

        conn.commit()

    print()
    print("QA users seeded successfully.")
    print()
    print("Test credentials:")
    for user in QA_USERS:
        print(f"  {user['email']} / {user['password']}")


if __name__ == "__main__":
    try:
        seed_qa_users()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
