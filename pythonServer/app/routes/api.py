from typing import Literal, Optional, Union

from fastapi import APIRouter, File, Form, UploadFile

from pythonServer.app.repositories.attendance import get_attendance_by_day
from pythonServer.app.repositories.roster import (
  add_student,
  get_student_name,
  get_student_name_map,
  get_students,
  ping,
  student_exists,
)
from pythonServer.app.services.face_recognition import FaceRecognitionService
from pythonServer.app.services.face_store import FaceStore


router = APIRouter()
face_store = FaceStore()
face_service: Optional[FaceRecognitionService] = None


def get_face_service() -> FaceRecognitionService:
  global face_service
  if face_service is None:
    face_service = FaceRecognitionService(face_store)
  return face_service


@router.post("/registerStudent")
async def register_student_image(
  id: Union[int, Literal["__TEMP__"]] = Form(...),
  image_file: UploadFile = File(...),
):
  image_bytes = await image_file.read()
  exists = True if id == "__TEMP__" else student_exists(str(id))
  return get_face_service().register_student_image(id, image_bytes, exists)


@router.post("/api/recognizeFrame")
async def recognize_frame(image_file: UploadFile = File(...)):
  image_bytes = await image_file.read()
  return get_face_service().recognize_frame(image_bytes, get_student_name_map())


@router.post("/delTempFace")
async def delete_temp_face():
  return get_face_service().clear_temp_face()


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
def get_roster_students():
  return get_students(face_store.registered_ids())


@router.post("/api/addStudents")
def create_student(fname: str = Form(...), lname: str = Form(...)):
  student_id = add_student(fname, lname)
  return {"status": "success", "id": student_id, "fname": fname, "lname": lname}


@router.get("/api/sql/attendanceByDay")
def attendance_by_day(dayStart: str, dayEnd: str):
  return {"attendance": get_attendance_by_day(dayStart, dayEnd)}
