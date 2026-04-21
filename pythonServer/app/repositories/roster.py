from datetime import datetime
from typing import Optional, Tuple

from pythonServer.app.db import get_db_connection


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


def _split_name(full_name: str) -> tuple[str, str]:
  parts = full_name.strip().split(None, 1)
  if not parts:
    return ("", "")
  if len(parts) == 1:
    return (parts[0], "")
  return (parts[0], parts[1])


def _normalize_class_name(class_name: Optional[str]) -> str:
  selected_class = (class_name or "All Students").strip() or "All Students"
  if selected_class == "Default: All Students":
    return "All Students"
  return selected_class


def _get_class_column(columns: set[str]) -> Optional[str]:
  for column_name in CLASS_COLUMN_CANDIDATES:
    if column_name in columns:
      return column_name
  return None


def _get_student_source(cursor) -> tuple[str, set[str]]:
  if _table_exists(cursor, "roster"):
    return ("roster", _get_table_columns(cursor, "roster"))
  if _table_exists(cursor, "students"):
    return ("students", _get_table_columns(cursor, "students"))
  raise RuntimeError("No supported student table was found")


def _courses_table_exists(cursor) -> bool:
  return _table_exists(cursor, "courses")


def _build_course_code(prefix: object, class_number: object, section: object) -> str:
  parts = [str(prefix).strip(), str(class_number).strip()]
  section_value = str(section or "").strip()
  if section_value:
    parts.append(section_value)
  return "-".join(part for part in parts if part)


def _split_course_meeting_time(meeting_time: Optional[str]) -> tuple[str, str]:
  raw_value = (meeting_time or "").strip()
  if not raw_value or "-" not in raw_value:
    return ("", "")

  start_raw, end_raw = [part.strip() for part in raw_value.split("-", 1)]
  for time_format in ("%I:%M %p", "%I %p"):
    try:
      start_value = datetime.strptime(start_raw, time_format).strftime("%H:%M")
      end_value = datetime.strptime(end_raw, time_format).strftime("%H:%M")
      return (start_value, end_value)
    except ValueError:
      continue
  return ("", "")


def _normalize_course_days(meeting_days: Optional[str]) -> str:
  raw_value = (meeting_days or "").strip()
  if not raw_value:
    return ""
  normalized = raw_value.replace("&", ",").replace("/", ",")
  return ",".join(part.strip() for part in normalized.split(",") if part.strip())


def _find_course_by_code(cursor, course_code: str) -> Optional[dict[str, object]]:
  if not _courses_table_exists(cursor):
    return None

  cursor.execute(
    """
    SELECT class_id, prefix, class_number, section, meeting_days, meeting_time, location
    FROM courses
    ORDER BY class_id;
    """
  )
  for row in cursor.fetchall():
    code = _build_course_code(row[1], row[2], row[3])
    if code == course_code:
      start_time, end_time = _split_course_meeting_time(row[5])
      return {
        "class_id": row[0],
        "label": code,
        "value": code,
        "start_time": start_time,
        "end_time": end_time,
        "days_of_week": _normalize_course_days(row[4]),
        "location": row[6] or "",
      }
  return None


def _ensure_student_class_column(
  cursor,
  table_name: str,
  columns: set[str],
) -> tuple[str, set[str]]:
  class_column = _get_class_column(columns)
  if class_column is not None:
    return (class_column, columns)

  cursor.execute(
    f"""
    ALTER TABLE {table_name}
    ADD COLUMN IF NOT EXISTS class_name VARCHAR(100) DEFAULT 'All Students';
    """
  )
  cursor.execute(
    f"""
    UPDATE {table_name}
    SET class_name = 'All Students'
    WHERE class_name IS NULL OR TRIM(CAST(class_name AS TEXT)) = '';
    """
  )
  refreshed_columns = _get_table_columns(cursor, table_name)
  return ("class_name", refreshed_columns)


def _ensure_classes_table(cursor) -> None:
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


def _normalize_default_all_students_records(cursor, table_name: str, class_column: Optional[str]) -> None:
  cursor.execute(
    """
    INSERT INTO classes (name)
    VALUES ('All Students')
    ON CONFLICT (name) DO NOTHING;
    """
  )
  cursor.execute("DELETE FROM classes WHERE name = 'Default: All Students';")
  if class_column:
    cursor.execute(
      f"""
      UPDATE {table_name}
      SET {class_column} = 'All Students'
      WHERE {class_column} = 'Default: All Students';
      """
    )


def get_student_name_map(class_name: Optional[str] = None) -> dict[str, tuple[str, str, str]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, columns = _get_student_source(cursor)
      class_column = _get_class_column(columns)

      if table_name == "roster":
        class_select = class_column or "'All Students'"
        query = f"SELECT stuid, fname, lname, {class_select} FROM roster"
        params: tuple[object, ...] = ()
        if class_name and class_name != "__all__" and class_column:
          query += f" WHERE {class_column} = %s"
          params = (class_name,)
        query += " ORDER BY lname, fname;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return {
          str(row[0]): (row[1], row[2], _normalize_class_name(row[3]))
          for row in rows
        }

      class_select = class_column or "'All Students'"
      query = f"SELECT id, name, {class_select} FROM students"
      params = ()
      if class_name and class_name != "__all__" and class_column:
        query += f" WHERE {class_column} = %s"
        params = (class_name,)
      query += " ORDER BY name;"
      cursor.execute(query, params)
      rows = cursor.fetchall()

  return {
    str(row[0]): (*_split_name(row[1]), _normalize_class_name(row[2]))
    for row in rows
  }


def get_available_classes() -> list[str]:
  return [class_info["value"] for class_info in get_available_class_details()]


def get_available_class_details() -> list[dict[str, object]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      if _courses_table_exists(cursor):
        course_details = [
          {
            "label": "All Students",
            "value": "All Students",
            "start_time": "",
            "end_time": "",
            "days_of_week": "",
          }
        ]
        cursor.execute(
          """
          SELECT class_id, prefix, class_number, section, meeting_days, meeting_time
          FROM courses
          ORDER BY prefix, class_number, section, class_id;
          """
        )
        for class_id, prefix, class_number, section, meeting_days, meeting_time in cursor.fetchall():
          class_code = _build_course_code(prefix, class_number, section)
          start_time, end_time = _split_course_meeting_time(meeting_time)
          course_details.append(
            {
              "label": class_code,
              "value": class_code,
              "class_id": class_id,
              "start_time": start_time,
              "end_time": end_time,
              "days_of_week": _normalize_course_days(meeting_days),
            }
          )
        return course_details

      _ensure_classes_table(cursor)
      table_name, columns = _get_student_source(cursor)
      class_column, columns = _ensure_student_class_column(cursor, table_name, columns)
      _normalize_default_all_students_records(cursor, table_name, class_column)
      classes: set[str] = set()
      class_details: dict[str, dict[str, object]] = {}
      cursor.execute(
        """
        SELECT name, start_time, end_time, COALESCE(days_of_week, '')
        FROM classes
        ORDER BY name;
        """
      )
      for name, start_time, end_time, days_of_week in cursor.fetchall():
        class_name = _normalize_class_name(str(name))
        classes.add(class_name)
        class_details[class_name] = {
          "label": class_name,
          "value": class_name,
          "start_time": start_time.strftime("%H:%M") if start_time else "",
          "end_time": end_time.strftime("%H:%M") if end_time else "",
          "days_of_week": days_of_week or "",
        }
      if class_column:
        cursor.execute(
          f"""
          SELECT DISTINCT {class_column}
          FROM {table_name}
          WHERE {class_column} IS NOT NULL
            AND TRIM(CAST({class_column} AS TEXT)) <> ''
          ORDER BY {class_column};
          """
        )
        classes.update(_normalize_class_name(str(row[0])) for row in cursor.fetchall())
    connection.commit()

  classes = sorted(classes)
  if not classes:
    classes = ["All Students"]

  return [
    class_details.get(
      class_name,
      {
        "label": class_name,
        "value": class_name,
        "start_time": "",
        "end_time": "",
        "days_of_week": "",
      },
    )
    for class_name in classes
  ]


def update_class_schedule(
  name: str,
  start_time: Optional[str],
  end_time: Optional[str],
  days_of_week: str,
) -> dict[str, object]:
  class_name = name.strip()
  if not class_name:
    raise ValueError("Class name cannot be empty")

  weekday_text = ", ".join(day.strip() for day in days_of_week.split(",") if day.strip())
  meeting_days = weekday_text.replace(", ", " & ")
  if start_time and end_time:
    start_display = datetime.strptime(start_time.strip(), "%H:%M").strftime("%I:%M %p").lstrip("0")
    end_display = datetime.strptime(end_time.strip(), "%H:%M").strftime("%I:%M %p").lstrip("0")
    meeting_time = f"{start_display} - {end_display}"
  else:
    meeting_time = ""

  cleaned_start = start_time.strip() if start_time else None
  cleaned_end = end_time.strip() if end_time else None
  cleaned_days = days_of_week.strip()

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      if _courses_table_exists(cursor):
        course = _find_course_by_code(cursor, class_name)
        if course is None:
          raise ValueError(f"Course {class_name} was not found")

        cursor.execute(
          """
          UPDATE courses
          SET meeting_days = %s,
              meeting_time = %s
          WHERE class_id = %s
          RETURNING class_id;
          """,
          (meeting_days, meeting_time, course["class_id"]),
        )
        row = cursor.fetchone()
        if row is None:
          raise ValueError(f"Course {class_name} was not found")
        connection.commit()
        return {
          "label": class_name,
          "value": class_name,
          "start_time": cleaned_start or "",
          "end_time": cleaned_end or "",
          "days_of_week": cleaned_days,
        }

      _ensure_classes_table(cursor)
      cursor.execute(
        """
        INSERT INTO classes (name, start_time, end_time, days_of_week)
        VALUES (%s, NULLIF(%s, '')::time, NULLIF(%s, '')::time, %s)
        ON CONFLICT (name) DO UPDATE
        SET start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            days_of_week = EXCLUDED.days_of_week
        RETURNING name, start_time, end_time, COALESCE(days_of_week, '');
        """,
        (class_name, cleaned_start or "", cleaned_end or "", cleaned_days),
      )
      row = cursor.fetchone()
    connection.commit()

  return {
    "label": row[0],
    "value": row[0],
    "start_time": row[1].strftime("%H:%M") if row[1] else "",
    "end_time": row[2].strftime("%H:%M") if row[2] else "",
    "days_of_week": row[3] or "",
  }


def add_class(name: str) -> str:
  class_name = _normalize_class_name(name)
  if not class_name:
    raise ValueError("Class name cannot be empty")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      if _courses_table_exists(cursor):
        raise ValueError("Classes are managed from the courses table.")
      _ensure_classes_table(cursor)
      cursor.execute(
        """
        INSERT INTO classes (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING;
        """,
        (class_name,),
      )
    connection.commit()
  return class_name


def remove_class(name: str) -> None:
  class_name = _normalize_class_name(name)
  if not class_name:
    raise ValueError("Class name cannot be empty")
  if class_name == "All Students":
    raise ValueError("All Students cannot be removed")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      if _courses_table_exists(cursor):
        raise ValueError("Classes are managed from the courses table.")
      _ensure_classes_table(cursor)
      table_name, columns = _get_student_source(cursor)
      class_column = _get_class_column(columns)
      if class_column:
        cursor.execute(
          f"""
          UPDATE {table_name}
          SET {class_column} = %s
          WHERE {class_column} = %s;
          """,
          ("All Students", class_name),
        )
      cursor.execute("DELETE FROM classes WHERE name = %s;", (class_name,))
    connection.commit()


def student_exists(student_id: str) -> bool:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, _columns = _get_student_source(cursor)
      id_column = "stuid" if table_name == "roster" else "id"
      cursor.execute(
        f"SELECT 1 FROM {table_name} WHERE {id_column} = %s LIMIT 1;",
        (student_id,),
      )
      return cursor.fetchone() is not None


def get_student_name(student_id: str) -> dict[str, str]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, _columns = _get_student_source(cursor)
      if table_name == "roster":
        cursor.execute(
          "SELECT fname, lname FROM roster WHERE stuid = %s LIMIT 1;",
          (student_id,),
        )
        row = cursor.fetchone()
        if row is None:
          raise LookupError(f"Student id {student_id} was not found")
        return {"fname": row[0], "lname": row[1], "fullName": f"{row[0]} {row[1]}"}

      cursor.execute(
        "SELECT name FROM students WHERE id = %s LIMIT 1;",
        (student_id,),
      )
      row = cursor.fetchone()

  if row is None:
    raise LookupError(f"Student id {student_id} was not found")

  fname, lname = _split_name(row[0])
  return {"fname": fname, "lname": lname, "fullName": row[0]}


def get_students(registered_ids: set[str]) -> list[tuple[str, str, int, bool, str]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, columns = _get_student_source(cursor)
      if table_name == "roster":
        class_column = _get_class_column(columns)
        if class_column:
          cursor.execute(
            f"""
            SELECT fname, lname, stuid, {class_column}
            FROM roster
            ORDER BY {class_column}, lname, fname;
            """
          )
        else:
          cursor.execute(
            """
            SELECT fname, lname, stuid, 'All Students'
            FROM roster
            ORDER BY lname, fname;
            """
          )
        rows = cursor.fetchall()
        return [
          (row[0], row[1], row[2], str(row[2]) in registered_ids, _normalize_class_name(row[3]))
          for row in rows
        ]

      order_column = "class_name, name" if "class_name" in columns else "name"
      class_select = "class_name" if "class_name" in columns else "'All Students'"
      cursor.execute(f"SELECT id, name, {class_select} FROM students ORDER BY {order_column};")
      rows = cursor.fetchall()

  students: list[tuple[str, str, int, bool, str]] = []
  for student_id, full_name, class_name in rows:
    fname, lname = _split_name(full_name)
    students.append(
      (
        fname,
        lname,
        student_id,
        str(student_id) in registered_ids,
        _normalize_class_name(class_name),
      )
    )
  return students


def get_students_for_class(class_name: Optional[str] = None) -> list[dict[str, object]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, columns = _get_student_source(cursor)
      class_column = _get_class_column(columns)

      if table_name == "roster":
        class_select = class_column or "'All Students'"
        query = f"SELECT stuid, fname, lname, {class_select} FROM roster"
        params: tuple[object, ...] = ()
        if class_name and class_name != "All Students" and class_column:
          query += f" WHERE {class_column} = %s"
          params = (class_name,)
        query += " ORDER BY lname, fname;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
          {
            "id": row[0],
            "name": f"{row[1]} {row[2]}".strip(),
            "class_name": _normalize_class_name(row[3]),
          }
          for row in rows
        ]

      class_select = class_column or "'All Students'"
      query = f"SELECT id, name, {class_select} FROM students"
      params = ()
      if class_name and class_name != "All Students" and class_column:
        query += f" WHERE {class_column} = %s"
        params = (class_name,)
      query += " ORDER BY name;"
      cursor.execute(query, params)
      rows = cursor.fetchall()

  return [
    {"id": row[0], "name": row[1], "class_name": _normalize_class_name(row[2])}
    for row in rows
  ]


def add_student(fname: str, lname: str, class_name: Optional[str] = None) -> int:
  full_name = " ".join(part for part in (fname.strip(), lname.strip()) if part).strip()
  if not full_name:
    raise ValueError("Student name cannot be empty")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, columns = _get_student_source(cursor)
      class_column, columns = _ensure_student_class_column(cursor, table_name, columns)
      selected_class = _normalize_class_name(class_name)
      if _courses_table_exists(cursor):
        if selected_class != "All Students" and _find_course_by_code(cursor, selected_class) is None:
          raise ValueError(f"Course {selected_class} was not found")
      else:
        _ensure_classes_table(cursor)
        cursor.execute(
          """
          INSERT INTO classes (name)
          VALUES (%s)
          ON CONFLICT (name) DO NOTHING;
          """,
          (selected_class,),
        )
      if table_name == "roster":
        if class_column:
          cursor.execute(
            f"""
            INSERT INTO roster (fname, lname, {class_column})
            VALUES (%s, %s, %s)
            RETURNING stuid;
            """,
            (fname, lname, selected_class),
          )
        else:
          cursor.execute(
            "INSERT INTO roster (fname, lname) VALUES (%s, %s) RETURNING stuid;",
            (fname, lname),
          )
        student_id = cursor.fetchone()[0]
      else:
        if class_column:
          cursor.execute(
            f"""
            INSERT INTO students (name, {class_column})
            VALUES (%s, %s)
            RETURNING id;
            """,
            (full_name, selected_class),
          )
        else:
          cursor.execute(
            "INSERT INTO students (name) VALUES (%s) RETURNING id;",
            (full_name,),
          )
        student_id = cursor.fetchone()[0]
    connection.commit()
  return student_id


def _get_next_new_student_number(cursor, table_name: str) -> int:
  if table_name == "roster":
    cursor.execute(
      """
      SELECT lname
      FROM roster
      WHERE fname = 'New' AND lname LIKE 'Student %';
      """
    )
    existing_names = [f"New {row[0]}" for row in cursor.fetchall()]
  else:
    cursor.execute(
      """
      SELECT name
      FROM students
      WHERE name LIKE 'New Student %';
      """
    )
    existing_names = [row[0] for row in cursor.fetchall()]

  highest_number = 0
  for name in existing_names:
    prefix = "New Student "
    if not name.startswith(prefix):
      continue
    suffix = name[len(prefix):].strip()
    if suffix.isdigit():
      highest_number = max(highest_number, int(suffix))

  return highest_number + 1


def add_camera_student(class_name: Optional[str] = None) -> dict[str, object]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, _columns = _get_student_source(cursor)
      next_number = _get_next_new_student_number(cursor, table_name)

  fname = "New"
  lname = f"Student {next_number}"
  selected_class = _normalize_class_name(class_name)
  student_id = add_student(fname, lname, selected_class)

  return {
    "id": student_id,
    "fname": fname,
    "lname": lname,
    "full_name": f"{fname} {lname}",
    "class_name": selected_class,
  }


def normalize_legacy_camera_students() -> list[dict[str, object]]:
  renamed_students: list[dict[str, object]] = []

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, _columns = _get_student_source(cursor)
      next_number = _get_next_new_student_number(cursor, table_name)

      if table_name == "roster":
        cursor.execute(
          """
          SELECT stuid
          FROM roster
          WHERE fname = 'Camera' AND lname LIKE 'Student %'
          ORDER BY stuid;
          """
        )
        student_ids = [row[0] for row in cursor.fetchall()]
        for student_id in student_ids:
          lname = f"Student {next_number}"
          cursor.execute(
            """
            UPDATE roster
            SET fname = 'New', lname = %s
            WHERE stuid = %s;
            """,
            (lname, student_id),
          )
          renamed_students.append(
            {"id": student_id, "fname": "New", "lname": lname, "full_name": f"New {lname}"}
          )
          next_number += 1
      else:
        cursor.execute(
          """
          SELECT id
          FROM students
          WHERE name LIKE 'Camera Student %'
          ORDER BY id;
          """
        )
        student_ids = [row[0] for row in cursor.fetchall()]
        for student_id in student_ids:
          name = f"New Student {next_number}"
          cursor.execute(
            """
            UPDATE students
            SET name = %s
            WHERE id = %s;
            """,
            (name, student_id),
          )
          renamed_students.append(
            {"id": student_id, "fname": "New", "lname": f"Student {next_number}", "full_name": name}
          )
          next_number += 1
    connection.commit()

  return renamed_students


def update_student_class(student_id: str, class_name: str) -> str:
  selected_class = _normalize_class_name(class_name)

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, columns = _get_student_source(cursor)
      class_column, _columns = _ensure_student_class_column(cursor, table_name, columns)
      if _courses_table_exists(cursor):
        if selected_class != "All Students" and _find_course_by_code(cursor, selected_class) is None:
          raise ValueError(f"Course {selected_class} was not found")
      else:
        _ensure_classes_table(cursor)
        cursor.execute(
          """
          INSERT INTO classes (name)
          VALUES (%s)
          ON CONFLICT (name) DO NOTHING;
          """,
          (selected_class,),
        )

      id_column = "stuid" if table_name == "roster" else "id"
      cursor.execute(
        f"""
        UPDATE {table_name}
        SET {class_column} = %s
        WHERE {id_column} = %s;
        """,
        (selected_class, student_id),
      )
      if cursor.rowcount == 0:
        raise LookupError(f"Student id {student_id} was not found")
    connection.commit()
  return selected_class


def update_student_name(student_id: str, fname: str, lname: str) -> dict[str, str]:
  first_name = fname.strip()
  last_name = lname.strip()
  full_name = " ".join(part for part in (first_name, last_name) if part).strip()
  if not full_name:
    raise ValueError("Student name cannot be empty")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, _columns = _get_student_source(cursor)
      id_column = "stuid" if table_name == "roster" else "id"
      if table_name == "roster":
        cursor.execute(
          """
          UPDATE roster
          SET fname = %s, lname = %s
          WHERE stuid = %s;
          """,
          (first_name, last_name, student_id),
        )
      else:
        cursor.execute(
          """
          UPDATE students
          SET name = %s
          WHERE id = %s;
          """,
          (full_name, student_id),
        )
      if cursor.rowcount == 0:
        raise LookupError(f"Student id {student_id} was not found")
    connection.commit()

  return {"fname": first_name, "lname": last_name, "fullName": full_name}


def delete_student(student_id: str) -> None:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      table_name, _columns = _get_student_source(cursor)
      id_column = "stuid" if table_name == "roster" else "id"
      cursor.execute(
        f"DELETE FROM {table_name} WHERE {id_column} = %s;",
        (student_id,),
      )
      if cursor.rowcount == 0:
        raise LookupError(f"Student id {student_id} was not found")
    connection.commit()


def ping() -> Optional[Tuple[int]]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute("SELECT 1;")
      return cursor.fetchone()
