from typing import Optional, Tuple
from pythonServer.app.db import get_db_connection


def get_student_name_map() -> dict[str, tuple[str, str]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute("SELECT stuid, fname, lname FROM roster;")
      rows = cursor.fetchall()
  return {str(row[0]): (row[1], row[2]) for row in rows}


def student_exists(student_id: str) -> bool:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute("SELECT 1 FROM roster WHERE stuid = %s LIMIT 1;", (student_id,))
      return cursor.fetchone() is not None


def get_student_name(student_id: str) -> dict[str, str]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute(
        "SELECT fname, lname FROM roster WHERE stuid = %s LIMIT 1;", (student_id,)
      )
      row = cursor.fetchone()

  if row is None:
    raise LookupError(f"Student id {student_id} was not found")

  return {"fname": row[0], "lname": row[1], "fullName": f"{row[0]} {row[1]}"}


def get_students(registered_ids: set[str]) -> list[tuple[str, str, int, bool]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute("SELECT fname, lname, stuid FROM roster ORDER BY lname, fname;")
      rows = cursor.fetchall()

  return [row + (str(row[2]) in registered_ids,) for row in rows]


def add_student(fname: str, lname: str) -> int:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute(
        "INSERT INTO roster (fname, lname) VALUES (%s, %s) RETURNING stuid;",
        (fname, lname),
      )
      student_id = cursor.fetchone()[0]
    connection.commit()
  return student_id


def ping() -> Optional[Tuple[int]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute("SELECT 1;")
      return cursor.fetchone()
