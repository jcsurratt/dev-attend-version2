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
CLASS_COLUMN_CANDIDATES = (
  "class_name",
  "class",
  "course_name",
  "course",
  "section",
  "class_id",
)


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
      id BIGSERIAL PRIMARY KEY,
      student_name VARCHAR(255) NOT NULL,
      day DATE NOT NULL DEFAULT CURRENT_DATE,
      student_id VARCHAR(50) NOT NULL,
      class_name VARCHAR(100) NOT NULL DEFAULT 'All Students',
      status VARCHAR(20) NOT NULL DEFAULT 'present',
      marked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      manual_override BOOLEAN NOT NULL DEFAULT FALSE
    );
    """
  )
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS student_name VARCHAR(255);")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS day DATE;")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS student_id VARCHAR(50);")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS class_name VARCHAR(100) DEFAULT 'All Students';")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'present';")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
  cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS manual_override BOOLEAN DEFAULT FALSE;")
  cursor.execute(
    """
    UPDATE attendance
    SET day = COALESCE(day, CURRENT_DATE),
        student_id = COALESCE(NULLIF(TRIM(student_id), ''), ''),
        class_name = COALESCE(NULLIF(TRIM(class_name), ''), 'All Students'),
        status = COALESCE(NULLIF(TRIM(status), ''), 'present'),
        marked_at = COALESCE(marked_at, CURRENT_TIMESTAMP),
        manual_override = COALESCE(manual_override, FALSE)
    WHERE day IS NULL
       OR student_id IS NULL
       OR class_name IS NULL
       OR status IS NULL
       OR marked_at IS NULL
       OR manual_override IS NULL;
    """
  )


def _get_student_source(cursor) -> tuple[str, str, set[str]]:
  if _table_exists(cursor, "roster"):
    columns = _get_table_columns(cursor, "roster")
    return ("roster", "stuid", columns)
  if _table_exists(cursor, "students"):
    columns = _get_table_columns(cursor, "students")
    return ("students", "id", columns)
  raise RuntimeError("No supported student table was found")


def _student_class_column(columns: set[str]) -> Optional[str]:
  for column_name in CLASS_COLUMN_CANDIDATES:
    if column_name in columns:
      return column_name
  return None


def _normalize_class_name(class_name: Optional[str]) -> str:
  selected_class = (class_name or "All Students").strip() or "All Students"
  if selected_class == "Default: All Students":
    return "All Students"
  return selected_class


def _build_course_code(prefix: object, class_number: object, section: object) -> str:
  parts: list[str] = []
  prefix_value = str(prefix or "").strip()
  number_value = "" if class_number is None else str(class_number).strip()
  section_value = str(section or "").strip()
  if prefix_value:
    parts.append(prefix_value)
  if number_value and number_value.lower() != "none":
    parts.append(number_value)
  if section_value and section_value.lower() != "none":
    parts.append(section_value)
  return "-".join(parts)


def _split_days(days_of_week: Optional[str]) -> set[str]:
  if not days_of_week:
    return set()
  return {
    day.strip().lower()
    for day in str(days_of_week).split(",")
    if day.strip().lower() in WEEKDAY_NAMES
  }


def _normalize_meeting_days(meeting_days: Optional[str]) -> str:
  raw_value = (meeting_days or "").strip()
  if not raw_value:
    return ""
  normalized = raw_value.replace("&", ",").replace("/", ",")
  return ",".join(part.strip() for part in normalized.split(",") if part.strip())


def _parse_meeting_time(meeting_time: Optional[str]) -> tuple[Optional[time], Optional[time]]:
  raw_value = (meeting_time or "").strip()
  if not raw_value or "-" not in raw_value:
    return (None, None)

  start_raw, end_raw = [part.strip() for part in raw_value.split("-", 1)]
  for time_format in ("%I:%M %p", "%I %p"):
    try:
      start_value = datetime.strptime(start_raw, time_format).time()
      end_value = datetime.strptime(end_raw, time_format).time()
      return (start_value, end_value)
    except ValueError:
      continue
  return (None, None)


def _is_class_today(days_of_week: Optional[str], now: datetime) -> bool:
  days = _split_days(days_of_week)
  if not days:
    return True
  return now.strftime("%A").lower() in days


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


def _course_code_sql(alias: str = "c") -> str:
  return (
    f"CONCAT_WS('-', NULLIF(TRIM(COALESCE({alias}.prefix, '')), ''), "
    f"NULLIF(TRIM(COALESCE({alias}.class_number::text, '')), ''), "
    f"NULLIF(TRIM(COALESCE({alias}.section, '')), ''))"
  )


def _get_class_schedule(cursor, class_name: str) -> Optional[dict[str, object]]:
  normalized_class = _normalize_class_name(class_name)
  if normalized_class == "All Students":
    return None

  if _table_exists(cursor, "courses"):
    course_code_sql = _course_code_sql("c")
    cursor.execute(
      f"""
      SELECT c.class_id, {course_code_sql}, c.meeting_days, c.meeting_time
      FROM courses c
      WHERE {course_code_sql} = %s
      LIMIT 1;
      """,
      (normalized_class,),
    )
    row = cursor.fetchone()
    if row is None:
      return None
    start_time, end_time = _parse_meeting_time(row[3])
    return {
      "class_id": row[0],
      "class_name": row[1],
      "start_time": start_time,
      "end_time": end_time,
      "days_of_week": _normalize_meeting_days(row[2]),
    }

  if _table_exists(cursor, "classes"):
    cursor.execute(
      """
      SELECT name, start_time, end_time, COALESCE(days_of_week, '')
      FROM classes
      WHERE name = %s
      LIMIT 1;
      """,
      (normalized_class,),
    )
    row = cursor.fetchone()
    if row is None:
      return None
    return {
      "class_id": row[0],
      "class_name": row[0],
      "start_time": row[1],
      "end_time": row[2],
      "days_of_week": row[3] or "",
    }

  return None


def _resolve_student(cursor, student_name: str, student_id: Optional[str], class_name: str) -> tuple[str, str]:
  table_name, id_column, columns = _get_student_source(cursor)
  class_column = _student_class_column(columns)
  normalized_class = _normalize_class_name(class_name)

  if student_id is not None and str(student_id).strip():
    student_key = str(student_id).strip()
    if table_name == "roster":
      cursor.execute(
        """
        SELECT TRIM(CONCAT(fname, ' ', lname))
        FROM roster
        WHERE stuid = %s
        LIMIT 1;
        """,
        (student_key,),
      )
    else:
      cursor.execute(
        """
        SELECT name
        FROM students
        WHERE id = %s
        LIMIT 1;
        """,
        (student_key,),
      )
    row = cursor.fetchone()
    return (student_key, row[0] if row and row[0] else student_name.strip())

  if table_name == "roster":
    name_sql = "TRIM(CONCAT(fname, ' ', lname))"
    base_query = f"SELECT stuid, {name_sql} FROM roster WHERE {name_sql} = %s"
  else:
    name_sql = "name"
    base_query = "SELECT id, name FROM students WHERE name = %s"

  params: tuple[object, ...] = (student_name.strip(),)
  if class_column:
    base_query += f" AND COALESCE({class_column}, 'All Students') = %s"
    params = (student_name.strip(), normalized_class)
  base_query += f" ORDER BY {id_column} LIMIT 1;"
  cursor.execute(base_query, params)
  row = cursor.fetchone()
  if row is None:
    raise LookupError(f"Student {student_name} was not found")
  return (str(row[0]), row[1] or student_name.strip())


def _serialize_attendance(row) -> dict[str, object]:
  return {
    "id": row[0],
    "student": row[1],
    "day": row[2].isoformat() if hasattr(row[2], "isoformat") else row[2],
    "student_id": str(row[3]) if row[3] is not None else "",
    "class_name": _normalize_class_name(row[4]),
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
        ORDER BY day DESC, student_name, id DESC;
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

  selected_class = _normalize_class_name(class_name)
  if selected_class == "All Students":
    raise ValueError("Attendance requires a course assignment.")

  now = datetime.now()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      schedule = _get_class_schedule(cursor, selected_class)
      if schedule is None:
        raise LookupError(f"Course {selected_class} was not found")

      student_key, resolved_name = _resolve_student(cursor, name, student_id, selected_class)
      status = _status_for_schedule(schedule, now)

      cursor.execute(
        """
        SELECT id, student_name, day, student_id, class_name, status, marked_at, manual_override
        FROM attendance
        WHERE student_id = %s
          AND class_name = %s
          AND day = CURRENT_DATE
        ORDER BY id DESC
        LIMIT 1;
        """,
        (student_key, selected_class),
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
              status = %s,
              marked_at = %s
          WHERE id = %s
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (resolved_name, next_status, now, existing["id"]),
        )
        row = cursor.fetchone()
      else:
        cursor.execute(
          """
          INSERT INTO attendance (student_name, day, student_id, class_name, status, marked_at, manual_override)
          VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, FALSE)
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (resolved_name, student_key, selected_class, status, now),
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
      table_name, id_column, columns = _get_student_source(cursor)
      class_column = _student_class_column(columns)
      if class_column is None:
        return

      if table_name == "roster":
        cursor.execute(
          f"""
          SELECT {id_column}, TRIM(CONCAT(fname, ' ', lname)), COALESCE({class_column}, 'All Students')
          FROM roster
          WHERE COALESCE({class_column}, 'All Students') <> 'All Students'
          ORDER BY {id_column};
          """
        )
      else:
        cursor.execute(
          f"""
          SELECT {id_column}, name, COALESCE({class_column}, 'All Students')
          FROM students
          WHERE COALESCE({class_column}, 'All Students') <> 'All Students'
          ORDER BY {id_column};
          """
        )
      students = cursor.fetchall()

      for student_id, student_name, class_name in students:
        normalized_class = _normalize_class_name(class_name)
        schedule = _get_class_schedule(cursor, normalized_class)
        if schedule is None:
          continue

        end_at = _combine_today(now, schedule.get("end_time"))
        if end_at is None:
          continue
        if now <= end_at:
          continue
        if not _is_class_today(str(schedule.get("days_of_week") or ""), now):
          continue

        cursor.execute(
          """
          SELECT 1
          FROM attendance
          WHERE student_id = %s
            AND class_name = %s
            AND day = CURRENT_DATE
          LIMIT 1;
          """,
          (str(student_id), normalized_class),
        )
        if cursor.fetchone() is not None:
          continue

        cursor.execute(
          """
          INSERT INTO attendance (student_name, day, student_id, class_name, status, marked_at, manual_override)
          VALUES (%s, CURRENT_DATE, %s, %s, 'absent', %s, FALSE);
          """,
          (student_name, str(student_id), normalized_class, now),
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
        WHERE day = CURRENT_DATE
        ORDER BY marked_at DESC, id DESC;
        """
      )
      rows = cursor.fetchall()

  attendance: dict[str, dict[str, object]] = {}
  for row in rows:
    record = _serialize_attendance(row)
    student_key = str(record["student_id"] or record["student"])
    if student_key not in attendance:
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

  selected_class = _normalize_class_name(class_name)
  if selected_class == "All Students":
    raise ValueError("Attendance requires a course assignment.")

  now = datetime.now()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_attendance_table(cursor)
      schedule = _get_class_schedule(cursor, selected_class)
      if schedule is None:
        raise LookupError(f"Course {selected_class} was not found")

      student_key, resolved_name = _resolve_student(cursor, student_name, student_id, selected_class)
      cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE student_id = %s
          AND class_name = %s
          AND day = CURRENT_DATE
        ORDER BY id DESC
        LIMIT 1;
        """,
        (student_key, selected_class),
      )
      existing = cursor.fetchone()

      if existing is None:
        cursor.execute(
          """
          INSERT INTO attendance (student_name, day, student_id, class_name, status, marked_at, manual_override)
          VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, TRUE)
          RETURNING id, student_name, day, student_id, class_name, status, marked_at, manual_override;
          """,
          (resolved_name, student_key, selected_class, selected_status, now),
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
          (resolved_name, selected_status, now, existing[0]),
        )
      row = cursor.fetchone()
    connection.commit()

  return _serialize_attendance(row)
