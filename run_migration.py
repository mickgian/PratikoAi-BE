#!/usr/bin/env python3
"""Run database migration manually."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set the environment for loading the database URL
os.environ.setdefault('APP_ENV', 'development')

# Import alembic and configuration
from alembic import command
from alembic.config import Config

def run_migration():
    """Run the database migration to add OAuth fields."""
    try:
        # Create alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Run the upgrade command
        print("Running database migration to add OAuth fields...")
        command.upgrade(alembic_cfg, "head")
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()