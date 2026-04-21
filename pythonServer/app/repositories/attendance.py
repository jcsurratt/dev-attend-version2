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


def _ensure_stu_attend_table(cursor) -> None:
  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS stu_attend (
      attend_id BIGSERIAL PRIMARY KEY,
      timestamp TIMESTAMP,
      stuid BIGINT REFERENCES roster(stuid),
      class_id BIGINT REFERENCES courses(class_id)
    );
    """
  )
  cursor.execute("ALTER TABLE stu_attend ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'present';")
  cursor.execute("ALTER TABLE stu_attend ADD COLUMN IF NOT EXISTS manual_override BOOLEAN DEFAULT FALSE;")


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


def _build_course_code(prefix: object, class_number: object, section: object) -> str:
  parts = [str(prefix).strip(), str(class_number).strip()]
  section_value = str(section or "").strip()
  if section_value:
    parts.append(section_value)
  return "-".join(part for part in parts if part)


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
    f"TRIM({alias}.prefix || '-' || {alias}.class_number::text || "
    f"CASE WHEN COALESCE(TRIM({alias}.section), '') <> '' THEN '-' || TRIM({alias}.section) ELSE '' END)"
  )


def _get_course_by_code(cursor, class_name: str) -> Optional[dict[str, object]]:
  if not class_name or class_name == "All Students" or not _table_exists(cursor, "courses"):
    return None

  course_code_sql = _course_code_sql("c")
  cursor.execute(
    f"""
    SELECT c.class_id, {course_code_sql} AS class_name, c.meeting_days, c.meeting_time
    FROM courses c
    WHERE {course_code_sql} = %s
    LIMIT 1;
    """,
    (class_name,),
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


def _resolve_student(cursor, student_name: str, student_id: Optional[str], class_name: str) -> tuple[str, str]:
  if student_id is not None and str(student_id).strip():
    student_key = str(student_id).strip()
    cursor.execute(
      """
      SELECT TRIM(CONCAT(fname, ' ', lname))
      FROM roster
      WHERE stuid = %s
      LIMIT 1;
      """,
      (student_key,),
    )
    row = cursor.fetchone()
    return (student_key, row[0] if row and row[0] else student_name.strip())

  cursor.execute(
    """
    SELECT stuid, TRIM(CONCAT(fname, ' ', lname))
    FROM roster
    WHERE TRIM(CONCAT(fname, ' ', lname)) = %s
      AND COALESCE(class_name, 'All Students') = %s
    ORDER BY stuid
    LIMIT 1;
    """,
    (student_name.strip(), class_name),
  )
  row = cursor.fetchone()
  if row is None:
    raise LookupError(f"Student {student_name} was not found in the roster")
  return (str(row[0]), row[1] or student_name.strip())


def _serialize_attendance(row) -> dict[str, object]:
  return {
    "id": row[0],
    "student": row[1],
    "day": row[2].isoformat() if hasattr(row[2], "isoformat") else row[2],
    "student_id": str(row[3]) if row[3] is not None else "",
    "class_name": row[4] or "All Students",
    "status": row[5] or "present",
    "marked_at": row[6].isoformat() if row[6] else "",
    "manual_override": bool(row[7]),
  }


def get_attendance_by_day(day_start: str, day_end: str) -> list[dict[str, object]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_stu_attend_table(cursor)
      course_code_sql = _course_code_sql("c")
      cursor.execute(
        f"""
        SELECT
          sa.attend_id,
          TRIM(CONCAT(r.fname, ' ', r.lname)) AS student_name,
          DATE(sa.timestamp) AS day,
          sa.stuid,
          COALESCE({course_code_sql}, 'All Students') AS class_name,
          COALESCE(sa.status, 'present') AS status,
          sa.timestamp,
          COALESCE(sa.manual_override, FALSE) AS manual_override
        FROM stu_attend sa
        LEFT JOIN roster r ON r.stuid = sa.stuid
        LEFT JOIN courses c ON c.class_id = sa.class_id
        WHERE DATE(sa.timestamp) BETWEEN %s AND %s
        ORDER BY DATE(sa.timestamp) DESC, student_name;
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
  if selected_class == "All Students":
    raise ValueError("Attendance requires a course assignment.")

  now = datetime.now()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_stu_attend_table(cursor)
      course = _get_course_by_code(cursor, selected_class)
      if course is None:
        raise LookupError(f"Course {selected_class} was not found")

      student_key, resolved_name = _resolve_student(cursor, name, student_id, selected_class)
      status = _status_for_schedule(course, now)

      cursor.execute(
        """
        SELECT
          sa.attend_id,
          TRIM(CONCAT(r.fname, ' ', r.lname)) AS student_name,
          DATE(sa.timestamp) AS day,
          sa.stuid,
          %s AS class_name,
          COALESCE(sa.status, 'present') AS status,
          sa.timestamp,
          COALESCE(sa.manual_override, FALSE) AS manual_override
        FROM stu_attend sa
        LEFT JOIN roster r ON r.stuid = sa.stuid
        WHERE sa.stuid = %s
          AND sa.class_id = %s
          AND DATE(sa.timestamp) = CURRENT_DATE
        ORDER BY sa.attend_id DESC
        LIMIT 1;
        """,
        (selected_class, student_key, course["class_id"]),
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
          UPDATE stu_attend
          SET timestamp = COALESCE(timestamp, %s),
              status = %s
          WHERE attend_id = %s
          RETURNING attend_id, %s, DATE(COALESCE(timestamp, %s)), stuid, %s, status, COALESCE(timestamp, %s), COALESCE(manual_override, FALSE);
          """,
          (now, next_status, existing["id"], resolved_name, now, selected_class, now),
        )
        row = cursor.fetchone()
      else:
        cursor.execute(
          """
          INSERT INTO stu_attend (timestamp, stuid, class_id, status, manual_override)
          VALUES (%s, %s, %s, %s, FALSE)
          RETURNING attend_id, %s, DATE(timestamp), stuid, %s, status, timestamp, COALESCE(manual_override, FALSE);
          """,
          (now, student_key, course["class_id"], status, resolved_name, selected_class),
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
      _ensure_stu_attend_table(cursor)
      if not _table_exists(cursor, "roster") or not _table_exists(cursor, "courses"):
        return

      course_code_sql = _course_code_sql("c")
      cursor.execute(
        f"""
        SELECT
          r.stuid,
          TRIM(CONCAT(r.fname, ' ', r.lname)) AS student_name,
          {course_code_sql} AS class_name,
          c.class_id,
          c.meeting_days,
          c.meeting_time
        FROM roster r
        JOIN courses c
          ON COALESCE(r.class_name, 'All Students') = {course_code_sql}
        WHERE COALESCE(r.class_name, 'All Students') <> 'All Students'
        ORDER BY r.stuid;
        """
      )

      for student_id, student_name, class_name, class_id, meeting_days, meeting_time in cursor.fetchall():
        start_time, end_time = _parse_meeting_time(meeting_time)
        schedule = {
          "start_time": start_time,
          "end_time": end_time,
          "days_of_week": _normalize_meeting_days(meeting_days),
        }
        end_at = _combine_today(now, schedule.get("end_time"))
        if end_at is None or now <= end_at or not _is_class_today(str(schedule.get("days_of_week") or ""), now):
          continue

        cursor.execute(
          """
          SELECT 1
          FROM stu_attend
          WHERE stuid = %s
            AND class_id = %s
            AND DATE(timestamp) = CURRENT_DATE
          LIMIT 1;
          """,
          (student_id, class_id),
        )
        if cursor.fetchone() is not None:
          continue

        cursor.execute(
          """
          INSERT INTO stu_attend (timestamp, stuid, class_id, status, manual_override)
          VALUES (%s, %s, %s, 'absent', FALSE);
          """,
          (now, student_id, class_id),
        )
    connection.commit()


def get_today_attendance_map() -> dict[str, dict[str, object]]:
  mark_absences_for_today()
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_stu_attend_table(cursor)
      course_code_sql = _course_code_sql("c")
      cursor.execute(
        f"""
        SELECT
          sa.attend_id,
          TRIM(CONCAT(r.fname, ' ', r.lname)) AS student_name,
          DATE(sa.timestamp) AS day,
          sa.stuid,
          COALESCE({course_code_sql}, 'All Students') AS class_name,
          COALESCE(sa.status, 'present') AS status,
          sa.timestamp,
          COALESCE(sa.manual_override, FALSE) AS manual_override
        FROM stu_attend sa
        LEFT JOIN roster r ON r.stuid = sa.stuid
        LEFT JOIN courses c ON c.class_id = sa.class_id
        WHERE DATE(sa.timestamp) = CURRENT_DATE
        ORDER BY sa.timestamp DESC, sa.attend_id DESC;
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

  selected_class = class_name.strip() or "All Students"
  if selected_class == "All Students":
    raise ValueError("Attendance requires a course assignment.")

  now = datetime.now()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_stu_attend_table(cursor)
      course = _get_course_by_code(cursor, selected_class)
      if course is None:
        raise LookupError(f"Course {selected_class} was not found")

      student_key, resolved_name = _resolve_student(cursor, student_name, student_id, selected_class)
      cursor.execute(
        """
        SELECT attend_id
        FROM stu_attend
        WHERE stuid = %s
          AND class_id = %s
          AND DATE(timestamp) = CURRENT_DATE
        ORDER BY attend_id DESC
        LIMIT 1;
        """,
        (student_key, course["class_id"]),
      )
      existing = cursor.fetchone()

      if existing is None:
        cursor.execute(
          """
          INSERT INTO stu_attend (timestamp, stuid, class_id, status, manual_override)
          VALUES (%s, %s, %s, %s, TRUE)
          RETURNING attend_id, %s, DATE(timestamp), stuid, %s, status, timestamp, TRUE;
          """,
          (now, student_key, course["class_id"], selected_status, resolved_name, selected_class),
        )
      else:
        cursor.execute(
          """
          UPDATE stu_attend
          SET timestamp = %s,
              status = %s,
              manual_override = TRUE
          WHERE attend_id = %s
          RETURNING attend_id, %s, DATE(timestamp), stuid, %s, status, timestamp, TRUE;
          """,
          (now, selected_status, existing[0], resolved_name, selected_class),
        )
      row = cursor.fetchone()
    connection.commit()

  return _serialize_attendance(row)
