import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _required_env(name: str) -> str:
  value = os.getenv(name)
  if value is None or not value.strip():
    raise RuntimeError(f"Missing required environment variable: {name}")
  return value


@dataclass(frozen=True)
class Settings:
  project_root: Path = PROJECT_ROOT
  server_root: Path = PROJECT_ROOT / "pythonServer"
  static_dir: Path = PROJECT_ROOT / "pythonServer" / "studentUI"
  js_globals_dir: Path = PROJECT_ROOT / "pythonServer" / "jsGlobals"
  torch_cache_dir: Path = PROJECT_ROOT / ".torch-cache"
  face_db_path: Path = PROJECT_ROOT / os.getenv("FACE_DB_PATH", "face_db.pkl")
  postgres_host: str = _required_env("POSTGRES_HOST")
  postgres_port: int = int(_required_env("POSTGRES_PORT"))
  postgres_db: str = _required_env("POSTGRES_DB")
  postgres_user: str = _required_env("POSTGRES_USER")
  postgres_password: str = _required_env("POSTGRES_PASSWORD")


@lru_cache
def get_settings() -> Settings:
  return Settings()
