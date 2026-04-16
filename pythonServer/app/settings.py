import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
  project_root: Path = PROJECT_ROOT
  server_root: Path = PROJECT_ROOT / "pythonServer"
  static_dir: Path = PROJECT_ROOT / "pythonServer" / "studentUI"
  js_globals_dir: Path = PROJECT_ROOT / "pythonServer" / "jsGlobals"
  torch_cache_dir: Path = PROJECT_ROOT / ".torch-cache"
  face_db_path: Path = PROJECT_ROOT / os.getenv("FACE_DB_PATH", "face_db.pkl")
  postgres_host: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
  postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
  postgres_db: str = os.getenv("POSTGRES_DB", "dev-attend")
  postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
  postgres_password: str = os.getenv("POSTGRES_PASSWORD", "dev-attend@3600")


@lru_cache
def get_settings() -> Settings:
  return Settings()
