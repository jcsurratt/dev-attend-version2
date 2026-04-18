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


def _ensure_classes_table(cursor) -> None:
  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS classes (
      name VARCHAR(100) PRIMARY KEY
    );
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
          str(row[0]): (row[1], row[2], row[3] or "All Students")
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
    str(row[0]): (*_split_name(row[1]), row[2] or "All Students")
    for row in rows
  }


def get_available_classes() -> list[str]:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_classes_table(cursor)
      table_name, columns = _get_student_source(cursor)
      class_column = _get_class_column(columns)
      classes: set[str] = set()
      cursor.execute("SELECT name FROM classes ORDER BY name;")
      classes.update(str(row[0]) for row in cursor.fetchall())
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
        classes.update(str(row[0]) for row in cursor.fetchall())

  classes = sorted(classes)
  return classes or ["All Students"]


def add_class(name: str) -> str:
  class_name = name.strip()
  if not class_name:
    raise ValueError("Class name cannot be empty")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
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
  class_name = name.strip()
  if not class_name:
    raise ValueError("Class name cannot be empty")
  if class_name == "All Students":
    raise ValueError("All Students cannot be removed")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
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
          (row[0], row[1], row[2], str(row[2]) in registered_ids, row[3])
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
        class_name or "All Students",
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
            "class_name": row[3] or "All Students",
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
    {"id": row[0], "name": row[1], "class_name": row[2] or "All Students"}
    for row in rows
  ]


def add_student(fname: str, lname: str, class_name: Optional[str] = None) -> int:
  full_name = " ".join(part for part in (fname.strip(), lname.strip()) if part).strip()
  if not full_name:
    raise ValueError("Student name cannot be empty")

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_classes_table(cursor)
      table_name, columns = _get_student_source(cursor)
      selected_class = (class_name or "All Students").strip() or "All Students"
      cursor.execute(
        """
        INSERT INTO classes (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING;
        """,
        (selected_class,),
      )
      if table_name == "roster":
        if class_name and "class_name" in columns:
          cursor.execute(
            """
            INSERT INTO roster (fname, lname, class_name)
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
        if "class_name" in columns:
          cursor.execute(
            """
            INSERT INTO students (name, class_name)
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
  selected_class = (class_name or "All Students").strip() or "All Students"
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
  selected_class = class_name.strip() or "All Students"

  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      _ensure_classes_table(cursor)
      table_name, columns = _get_student_source(cursor)
      class_column = _get_class_column(columns)
      if class_column is None:
        raise RuntimeError("Students do not have a class column")

      id_column = "stuid" if table_name == "roster" else "id"
      cursor.execute(
        """
        INSERT INTO classes (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING;
        """,
        (selected_class,),
      )
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
