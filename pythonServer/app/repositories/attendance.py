from pythonServer.app.db import get_db_connection


def get_attendance_by_day(day_start: str, day_end: str) -> list[dict[str, object]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute(
        "SELECT id, student_name, day FROM attendance WHERE day BETWEEN %s AND %s;",
        (day_start, day_end),
      )
      rows = cursor.fetchall()

  return [{"id": row[0], "student": row[1], "day": row[2]} for row in rows]
