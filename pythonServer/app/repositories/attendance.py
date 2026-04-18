from datetime import datetime, time, timedelta
from typing import Optional

from pythonServer.app.db import get_db_connection


VALID_STATUSES = {"present", "tardy", "absent"}
WEEKDAY_NAMES = {
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
}


def _table_exists(cursor, table_name: str) -> bool:
  cursor.execute(
    """
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = %s
    LIMIT 1;
    """,
    (table_name,),
  )
  return cursor.fetchone() is not None


def _get_table_columns(cursor, table_name: str) -> set[str]:
  cursor.execute(
    """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = %s;
    """,
    (table_name,),
  )
  return {row[0] for row in cursor.fetchall()}


def _ensure_attendance_table(cursor) -> None:
  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS attendance (
      id SERIAL PRIMARY KEY,
      student_name VARCHAR(200),
      day DATE DEFAULT CURRENT_DATE
    );
    """
  )
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS student_id VARCHAR(100);")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS class_name VARCHAR(100);")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'present';")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS marked_at TIMESTAMP;")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS manual_override BOOLEAN DEFAULT FALSE;")


def _ensure_classes_schedule_columns(cursor) -> None:
  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS classes (
      name VARCHAR(100) PRIMARY KEY,
      start_time TIME,
      end_time TIME,
      days_of_week TEXT DEFAULT ''
    );
    """
  )
  cursor.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS start_time TIME;")
  cursor.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS end_time TIME;")
  cursor.execute("ALTER TABLE classes ADD COLUMN IF NOT EXISTS days_of_week TEXT DEFAULT '';")


def _get_student_source(cursor) -> tuple[str, str, set[str]]:
  if _table_exists(cursor, "roster"):
    columns = _get_table_columns(cursor, "roster")
    return ("roster", "stuid", columns)
  if _table_exists(cursor, "students"):
    columns = _get_table_columns(cursor, "students")
    return ("students", "id", columns)
  raise RuntimeError("No supported student table was found")


def _student_class_column(columns: set[str]) -> Optional[str]:
  for column_name in ("class_name", "class", "course_name", "course", "section", "class_id"):
    if column_name in columns:
      return column_name
  return None


def _split_days(days_of_week: Optional[str]) -> set[str]:
  if not days_of_week:
    return set()
  return {
    day.strip().lower()
    for day in days_of_week.split(",")
    if day.strip().lower() in WEEKDAY_NAMES
  }


def _is_class_today(days_of_week: Optional[str], now: datetime) -> bool:
  days = _split_days(days_of_week)
  if not days:
    return True
  return now.strftime("%A").lower() in days


def _get_class_schedule(cursor, class_name: str) -> dict[str, object]:
  _ensure_classes_schedule_columns(cursor)
  cursor.execute(
    """
    SELECT start_time, end_time, COALESCE(days_of_week, '')
    FROM classes
    WHERE name = %s
    LIMIT 1;
    """,
    (class_name,),
  )
  row = cursor.fetchone()
  if row is None:
    return {"start_time": None, "end_time": None, "days_of_week": ""}
  return {"start_time": row[0], "end_time": row[1], "days_of_week": row[2] or ""}


def _combine_today(now: datetime, value: Optional[time]) -> Optional[datetime]:
  if value is None:
    return None
  return datetime.combine(now.date(), value)


def _status_for_schedule(schedule: dict[str, object], now: datetime) -> str:
  start_at = _combine_today(now, schedule.get("start_time"))
  end_at = _combine_today(now, schedule.get("end_time"))
  days_of_week = str(schedule.get("days_of_week") or "")

  if not _is_class_today(days_of_week, now):
    return "present"
  if start_at is None:
    return "present"
  if now <= start_at + timedelta(minutes=15):
    return "present"
  if end_at is None or now <= end_at:
    return "tardy"
  return "absent"


def _serialize_attendance(row) -> dict[str, object]:
  return {
    "id": row[0],
    "student": row[1],
    "day": row[2].isoformat() if hasattr(row[2], "isoformat") else row[2],
    "student_id": row[3],
    "class_name": row[4],
    "status": row[5] or "present",
    "marked_at": row[6].isoformat() if row[6] else "",
    "manual_override": bool(row[7]),
  }


def get_attendance_by_day(day_start: str, day_end: str) -> list[dict[str, object]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      cursor.execute(
        """
        SELECT id, student_name, day, student_id, class_name, status, marked_at, manual_override
        FROM attendance
        WHERE day BETWEEN %s AND %s
        ORDER BY day DESC, student_name;
        """,
        (day_start, day_end),
      )
      rows = cursor.fetchall()

  return [_serialize_attendance(row) for row in rows]


def mark_student_attendance(
  student_name: str,
  student_id: Optional[str] = None,
  class_name: Optional[str] = None,
) -> dict[str, object]:
  name = student_name.strip()
  if not name:
    raise ValueError("Student name cannot be empty")

  selected_class = (class_name or "All Students").strip() or "All Students"
  student_key = str(student_id).strip() if student_id is not None else None
  now = datetime.now()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      schedule = _get_class_schedule(cursor, selected_class)
      status = _status_for_schedule(schedule, now)

      if student_key:
        cursor.execute(
          """
          SELECT id, student_name, day, student_id, class_name, status, marked_at, manual_override
          FROM attendance
          WHERE student_id = %s AND class_name = %s AND day = CURRENT_DATE
          ORDER BY id DESC
          LIMIT 1;
          """,
          (student_key, selected_class),
        )
      else:
        cursor.execute(
          """
          SELECT id, student_name, day, student_id, class_name, status, marked_at, manual_override
          FROM attendance
          WHERE student_name = %s AND day = CURRENT_DATE
          ORDER BY id DESC
          LIMIT 1;
          """,
          (name,),
        )

      existing_row = cursor.fetchone()
      if existing_row is not None:
        existing = _serialize_attendance(existing_row)
        if existing["manual_override"]:
          return existing

        existing_status = str(existing["status"])
        next_status = existing_status
        if existing_status == "absent" and status in ("present", "tardy"):
          next_status = status
        elif existing_status not in ("present", "tardy"):
          next_status = status

        cursor.execute(
          """
          UPDATE attendance
          SET student_name = %s,
              student_id = COALESCE(%s, student_id),
              class_name = %s,
              status = %s,
              marked_at = COALESCE(marked_at, %s)
          WHERE id = %s
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (name, student_key, selected_class, next_status, now, existing["id"]),
        )
        row = cursor.fetchone()
      else:
        cursor.execute(
          """
          INSERT INTO attendance (student_name, day, student_id, class_name, status, marked_at)
          VALUES (%s, CURRENT_DATE, %s, %s, %s, %s)
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (name, student_key, selected_class, status, now),
        )
        row = cursor.fetchone()
    connection.commit()

  return _serialize_attendance(row)


def mark_student_present(student_name: str) -> dict[str, object]:
  return mark_student_attendance(student_name)


def mark_absences_for_today() -> None:
  now = datetime.now()
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      _ensure_classes_schedule_columns(cursor)
      table_name, id_column, columns = _get_student_source(cursor)
      class_column = _student_class_column(columns)
      if class_column is None:
        return

      if table_name == "roster":
        cursor.execute(
          f"""
          SELECT stuid, TRIM(CONCAT(fname, ' ', lname)) AS student_name, {class_column}
          FROM roster
          WHERE {class_column} IS NOT NULL
            AND TRIM(CAST({class_column} AS TEXT)) <> '';
          """
        )
      else:
        cursor.execute(
          f"""
          SELECT {id_column}, name, {class_column}
          FROM students
          WHERE {class_column} IS NOT NULL
            AND TRIM(CAST({class_column} AS TEXT)) <> '';
          """
        )

      students = cursor.fetchall()
      for student_id, student_name, class_name in students:
        selected_class = class_name or "All Students"
        schedule = _get_class_schedule(cursor, selected_class)
        end_at = _combine_today(now, schedule.get("end_time"))
        if end_at is None or now <= end_at or not _is_class_today(str(schedule.get("days_of_week") or ""), now):
          continue

        cursor.execute(
          """
          SELECT 1
          FROM attendance
          WHERE student_id = %s AND class_name = %s AND day = CURRENT_DATE
          LIMIT 1;
          """,
          (str(student_id), selected_class),
        )
        if cursor.fetchone() is not None:
          continue

        cursor.execute(
          """
          INSERT INTO attendance (student_name, day, student_id, class_name, status, marked_at)
          VALUES (%s, CURRENT_DATE, %s, %s, 'absent', %s);
          """,
          (student_name, str(student_id), selected_class, now),
        )
    connection.commit()


def get_today_attendance_map() -> dict[str, dict[str, object]]:
  mark_absences_for_today()
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      cursor.execute(
        """
        SELECT id, student_name, day, student_id, class_name, status, marked_at, manual_override
        FROM attendance
        WHERE day = CURRENT_DATE;
        """
      )
      rows = cursor.fetchall()

  attendance: dict[str, dict[str, object]] = {}
  for row in rows:
    record = _serialize_attendance(row)
    student_key = str(record["student_id"] or record["student"])
    attendance[student_key] = record
  return attendance


def update_attendance_status(
  student_id: str,
  student_name: str,
  class_name: str,
  status: str,
) -> dict[str, object]:
  selected_status = status.strip().lower()
  if selected_status not in VALID_STATUSES:
    raise ValueError("Attendance status must be present, tardy, or absent")

  name = student_name.strip()
  selected_class = class_name.strip() or "All Students"
  now = datetime.now()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE student_id = %s AND class_name = %s AND day = CURRENT_DATE
        ORDER BY id DESC
        LIMIT 1;
        """,
        (student_id, selected_class),
      )
      existing = cursor.fetchone()
      if existing is None:
        cursor.execute(
          """
          INSERT INTO attendance (
            student_name, day, student_id, class_name, status, marked_at, manual_override
          )
          VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, TRUE)
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (name, student_id, selected_class, selected_status, now),
        )
      else:
        cursor.execute(
          """
          UPDATE attendance
          SET student_name = %s,
              status = %s,
              marked_at = %s,
              manual_override = TRUE
          WHERE id = %s
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (name, selected_status, now, existing[0]),
        )
      row = cursor.fetchone()
    connection.commit()

  return _serialize_attendance(row)
