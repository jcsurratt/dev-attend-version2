import csv
import io
from typing import Literal, Optional, Union

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from pythonServer.app.repositories.attendance import (
  get_attendance_export_for_class,
  get_attendance_by_day,
  get_today_attendance_map,
  mark_absences_for_today,
  mark_student_attendance,
  mark_student_present,
  update_attendance_status,
)
from pythonServer.app.repositories.roster import (
  add_camera_student,
  add_class,
  add_student,
  delete_student,
  get_available_class_details,
  get_student_name,
  get_student_name_map,
  get_students,
  get_students_for_class,
  normalize_legacy_camera_students,
  ping,
  remove_class,
  student_exists,
  update_class_schedule,
  update_student_class,
  update_student_name,
)
from pythonServer.app.services.face_recognition import FaceRecognitionService
from pythonServer.app.services.face_store import FaceStore


router = APIRouter()
face_store = FaceStore()
face_service: Optional[FaceRecognitionService] = None
face_service_error: Optional[str] = None


def get_face_service() -> FaceRecognitionService:
  global face_service, face_service_error
  if face_service is None:
    try:
      face_service = FaceRecognitionService(face_store)
      face_service_error = None
    except Exception as error:
      face_service_error = str(error)
      raise RuntimeError(face_service_error) from error
  return face_service


@router.post("/registerStudent")
async def register_student_image(
  id: Union[int, Literal["__TEMP__"]] = Form(...),
  image_file: UploadFile = File(...),
):
  image_bytes = await image_file.read()
  exists = True if id == "__TEMP__" else student_exists(str(id))
  try:
    return get_face_service().register_student_image(id, image_bytes, exists)
  except RuntimeError as error:
    return JSONResponse(
      status_code=503,
      content={
        "status": "error",
        "message": f"Face recognition is unavailable: {error}",
      },
    )


@router.post("/api/recognizeFrame")
async def recognize_frame(
  image_file: UploadFile = File(...),
  class_name: Optional[str] = Form(default=None),
):
  image_bytes = await image_file.read()
  try:
    student_name_map = get_student_name_map()
  except Exception:
    student_name_map = {}
  try:
    return get_face_service().recognize_frame(
      image_bytes,
      student_name_map,
    )
  except RuntimeError as error:
    return JSONResponse(
      status_code=503,
      content={
        "status": "error",
        "message": f"Face recognition is unavailable: {error}",
        "faces": [],
      },
    )


@router.post("/delTempFace")
async def delete_temp_face():
  removed = face_store.remove_student("__TEMP__")
  if not removed:
    return {"status": "success", "message": "No temporary face data was present."}
  return {"status": "success", "message": "Temporary face data was cleared."}


@router.post("/api/unregisterStudent")
def unregister_student(
  studentId: str = Form(...),
  action: str = Form(default="unregister"),
  deleteStudent: str = Form(default="false"),
):
  should_delete = action == "delete" or deleteStudent.lower() in ("1", "true", "yes")
  if should_delete:
    try:
      face_store.remove_student(studentId)
      delete_student(studentId)
      return {"status": "success", "message": f"Student {studentId} was deleted."}
    except Exception as error:
      return {"status": "error", "message": str(error)}

  removed = face_store.remove_student(studentId)

  if not removed:
    return {"status": "error", "message": f"Student {studentId} is not registered."}
  return {"status": "success", "message": f"Student {studentId} was unregistered."}


@router.post("/api/deleteStudent")
def delete_roster_student(studentId: str = Form(...)):
  try:
    face_store.remove_student(studentId)
    delete_student(studentId)
    return {"status": "success", "id": studentId}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.get("/api/getUserName")
def get_user_name(id: str):
  try:
    return {"status": "success", **get_student_name(id)}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.get("/api/testdb")
def test_database():
  return {"database_working": ping()}


@router.get("/api/students")
def get_roster_students(class_name: Optional[str] = None):
  if class_name is not None:
    return get_students_for_class(class_name)
  mark_absences_for_today()
  attendance_by_student = get_today_attendance_map()
  students = get_students(face_store.registered_ids())
  return [
    (
      fname,
      lname,
      student_id,
      is_registered,
      class_name,
      attendance_by_student.get(str(student_id), {}),
    )
    for fname, lname, student_id, is_registered, class_name in students
  ]


@router.get("/api/classStudents")
def get_class_students(class_name: str):
  mark_absences_for_today()
  attendance_by_student = get_today_attendance_map()
  students = get_students_for_class(class_name)
  for student in students:
    student["attendance"] = attendance_by_student.get(str(student["id"]), {})
  return students


@router.get("/api/classes")
def get_classes():
  try:
    options = get_available_class_details()
  except Exception:
    options = [{"label": "All Students", "value": "All Students", "start_time": "", "end_time": "", "days_of_week": ""}]
  return {"classes": options}


@router.post("/api/classes")
def create_class(name: str = Form(...)):
  try:
    class_name = add_class(name)
    return {"status": "success", "name": class_name}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/classes/remove")
def delete_class(name: str = Form(...)):
  try:
    remove_class(name)
    return {"status": "success", "name": name}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/classes/schedule")
def change_class_schedule(
  name: str = Form(...),
  start_time: Optional[str] = Form(default=None),
  end_time: Optional[str] = Form(default=None),
  days_of_week: str = Form(default=""),
):
  try:
    class_info = update_class_schedule(name, start_time, end_time, days_of_week)
    return {"status": "success", "class": class_info}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/addStudents")
def create_student(
  fname: str = Form(...),
  lname: str = Form(...),
  class_name: Optional[str] = Form(default=None),
):
  student_id = add_student(fname, lname, class_name)
  return {
    "status": "success",
    "id": student_id,
    "fname": fname,
    "lname": lname,
    "class_name": class_name or "All Students",
  }


@router.post("/api/cameraRegistrationStudent")
def create_camera_registration_student(
  class_name: Optional[str] = Form(default=None),
):
  try:
    student = add_camera_student(class_name)
    return {"status": "success", **student}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/students/normalizeCameraNames")
def normalize_camera_student_names():
  try:
    renamed_students = normalize_legacy_camera_students()
    return {"status": "success", "students": renamed_students}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/students/updateClass")
def change_student_class(
  studentId: str = Form(...),
  class_name: str = Form(...),
):
  try:
    selected_class = update_student_class(studentId, class_name)
    return {"status": "success", "id": studentId, "class_name": selected_class}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/students/updateName")
def change_student_name(
  studentId: str = Form(...),
  fname: str = Form(...),
  lname: str = Form(default=""),
):
  try:
    student = update_student_name(studentId, fname, lname)
    return {"status": "success", "id": studentId, **student}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.get("/api/sql/attendanceByDay")
def attendance_by_day(dayStart: str, dayEnd: str):
  return {"attendance": get_attendance_by_day(dayStart, dayEnd)}


@router.get("/api/attendance/export")
def export_attendance(class_name: str):
  try:
    rows = get_attendance_export_for_class(class_name)
  except Exception as error:
    return JSONResponse(
      status_code=400,
      content={"status": "error", "message": str(error)},
    )

  output = io.StringIO()
  writer = csv.DictWriter(
    output,
    fieldnames=[
      "day",
      "class_code",
      "student_id",
      "student_name",
      "attendance_status",
      "marked_at",
      "manual_override",
    ],
  )
  writer.writeheader()
  writer.writerows(rows)
  output.seek(0)

  safe_class_name = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in class_name)
  filename = f"attendance-{safe_class_name or 'class'}-{rows[0]['day'] if rows else 'today'}.csv"

  return StreamingResponse(
    iter([output.getvalue()]),
    media_type="text/csv",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )


@router.post("/api/attendance/markPresent")
def mark_present(
  studentName: str = Form(...),
  studentId: Optional[str] = Form(default=None),
  class_name: Optional[str] = Form(default=None),
):
  try:
    if studentId or class_name:
      attendance = mark_student_attendance(studentName, studentId, class_name)
    else:
      attendance = mark_student_present(studentName)
    return {"status": "success", "attendance": attendance}
  except Exception as error:
    return {"status": "error", "message": str(error)}


@router.post("/api/attendance/updateStatus")
def change_attendance_status(
  studentId: str = Form(...),
  studentName: str = Form(...),
  class_name: str = Form(...),
  status: str = Form(...),
):
  try:
    attendance = update_attendance_status(studentId, studentName, class_name, status)
    return {"status": "success", "attendance": attendance}
  except Exception as error:
    return {"status": "error", "message": str(error)}
