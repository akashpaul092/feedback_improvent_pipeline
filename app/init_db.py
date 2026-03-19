"""Database initialization - runs Alembic migrations to create/update tables."""
import subprocess
import sys


def init_db():
    """Run Alembic migrations. Tables are created/updated automatically."""
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])


if __name__ == "__main__":
    init_db()
    print("Database migrations applied.")
