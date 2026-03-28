import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.makedirs(BASE_DIR / "instance", exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise ValueError("SECRET_KEY environment variable is required in production")
        SECRET_KEY = "dev-only-secret-do-not-use-in-production"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'database.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
