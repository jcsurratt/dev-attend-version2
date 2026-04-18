from typing import Literal, Optional, Union

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from pythonServer.app.repositories.attendance import (
  get_attendance_by_day,
  mark_student_present,
)
from pythonServer.app.repositories.roster import (
  add_class,
  add_student,
  delete_student,
  get_available_classes,
  get_student_name,
  get_student_name_map,
  get_students,
  get_students_for_class,
  ping,
  remove_class,
  student_exists,
  update_student_class,
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
  return get_face_service().clear_temp_face()


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
  return get_students(face_store.registered_ids())


@router.get("/api/classStudents")
def get_class_students(class_name: str):
  return get_students_for_class(class_name)


@router.get("/api/classes")
def get_classes():
  try:
    classes = get_available_classes()
  except Exception:
    classes = ["All Students"]
  options = [{"label": class_name, "value": class_name} for class_name in classes]
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


@router.get("/api/sql/attendanceByDay")
def attendance_by_day(dayStart: str, dayEnd: str):
  return {"attendance": get_attendance_by_day(dayStart, dayEnd)}


@router.post("/api/attendance/markPresent")
def mark_present(studentName: str = Form(...)):
  try:
    attendance = mark_student_present(studentName)
    return {"status": "success", "attendance": attendance}
  except Exception as error:
    return {"status": "error", "message": str(error)}
