from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = "hanoi-fishing-secret-key"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'fishing_ponds.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
