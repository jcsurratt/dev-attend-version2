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


def mark_student_present(student_name: str) -> dict[str, object]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute(
        """
        SELECT id, student_name, day
        FROM attendance
        WHERE student_name = %s AND day = CURRENT_DATE
        LIMIT 1;
        """,
        (student_name,),
      )
      existing_row = cursor.fetchone()
      if existing_row is not None:
        return {
          "id": existing_row[0],
          "student": existing_row[1],
          "day": existing_row[2],
        }

      cursor.execute(
        """
        INSERT INTO attendance (student_name, day)
        VALUES (%s, CURRENT_DATE)
        RETURNING id, student_name, day;
        """,
        (student_name,),
      )
      row = cursor.fetchone()
    connection.commit()

  return {"id": row[0], "student": row[1], "day": row[2]}
