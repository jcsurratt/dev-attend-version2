from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection as PgConnection

from .settings import get_settings


@contextmanager
def get_db_connection() -> Iterator[PgConnection]:
  settings = get_settings()
  connection = psycopg2.connect(
    dbname=settings.postgres_db,
    user=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
  )
  try:
    yield connection
  finally:
    connection.close()
