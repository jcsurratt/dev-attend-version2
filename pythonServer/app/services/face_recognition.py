import gc
import io
import os
from typing import Literal, Optional, TypedDict, Union

import torch
from PIL import Image
from PIL.Image import Image as ImageType
from facenet_pytorch import InceptionResnetV1, MTCNN
from torch import Tensor

from pythonServer.app.settings import get_settings

from .face_store import FaceDatabase, FaceStore


class StudentMutationResponse(TypedDict):
  status: str
  message: str


class FaceResponse(TypedDict):
  box: list[float]
  name: str
  id: int
  class_name: str
  distance: float
  direction_x: float
  direction_y: float


class FaceListResponse(TypedDict):
  faces: list[FaceResponse]


class FaceRecognitionService:
  def __init__(self, face_store: FaceStore) -> None:
    self._face_store = face_store
    settings = get_settings()
    settings.torch_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_HOME", str(settings.torch_cache_dir))
    self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    self._mtcnn = MTCNN(keep_all=True, device=self._device)
    self._resnet = InceptionResnetV1(pretrained="vggface2").eval().to(self._device)

  def register_student_image(
    self,
    student_id: Union[int, Literal["__TEMP__"]],
    image_bytes: bytes,
    student_exists: bool,
  ) -> StudentMutationResponse:
    face_db = self._face_store.load()
    student_key = str(student_id)
    image = self._load_image(image_bytes)
    if image is None:
      return {"status": "error", "message": "Invalid image format"}

    faces = self._mtcnn(image)
    if faces is None:
      return {"status": "error", "message": "No face detected in the provided image."}

    if student_key != "__TEMP__" and not student_exists:
      return {
        "status": "error",
        "message": f"{student_key} that id doesn't exist in the database",
      }

    embedding = self._resnet(faces[0].unsqueeze(0).to(self._device)).detach().cpu()
    face_db.setdefault(student_key, []).append(embedding)
    self._face_store.save(face_db, include_temp=student_key == "__TEMP__")
    return {
      "status": "success",
      "message": f"Student {student_key} registered with uploaded image.",
    }

  def recognize_frame(
    self,
    image_bytes: bytes,
    student_names: dict[str, tuple[str, str, str]],
  ) -> FaceListResponse:
    face_db = self._face_store.load()
    image = self._load_image(image_bytes)
    if image is None:
      return {"faces": []}

    boxes, _probs, landmarks = self._mtcnn.detect(image, landmarks=True)
    faces = None
    if boxes is not None:
      faces = self._mtcnn.extract(image, boxes, save_path=None)

    results: list[FaceResponse] = []
    if boxes is None or faces is None or landmarks is None:
      return {"faces": results}

    for index, box in enumerate(boxes.tolist()):
      if index >= len(faces):
        continue

      current_face_tensor = faces[index].unsqueeze(0).to(self._device)
      current_embedding = self._resnet(current_face_tensor).detach().cpu()
      student_key, best_distance = self._find_best_match(face_db, current_embedding)

      face_landmarks = landmarks[index]
      left_eye_x = float(face_landmarks[0][0])
      left_eye_y = float(face_landmarks[0][1])
      right_eye_x = float(face_landmarks[1][0])
      right_eye_y = float(face_landmarks[1][1])
      nose_x = float(face_landmarks[2][0])
      nose_y = float(face_landmarks[2][1])

      eye_distance = right_eye_x - left_eye_x or 1
      direction_x = (nose_x - left_eye_x) / eye_distance
      eye_mid_y = (left_eye_y + right_eye_y) / 2.0
      direction_y = (nose_y - eye_mid_y) / eye_distance

      if student_key == "__TEMP__":
        face_name = "__TEMP__"
        face_class = ""
      elif student_key in student_names:
        fname, lname, class_name = student_names[student_key]
        face_name = " ".join((fname, lname)).strip()
        face_class = class_name or "All Students"
      else:
        face_name = "Unknown"
        face_class = ""

      results.append(
        {
          "box": [float(value) for value in box],
          "name": face_name,
          "id": int(student_key) if student_key.isdigit() else -1,
          "class_name": face_class,
          "distance": round(best_distance, 2),
          "direction_x": round(((direction_x - 0.5) * -1) + 0.5, 3),
          "direction_y": round(direction_y, 3),
        }
      )

    return {"faces": results}

  def clear_temp_face(self) -> StudentMutationResponse:
    face_db = self._face_store.load()
    if "__TEMP__" not in face_db:
      return {"status": "error", "message": "Identity not found in AI database."}

    embeddings: list[Tensor] = face_db.pop("__TEMP__")
    for embedding in embeddings:
      del embedding

    self._face_store.save(face_db)
    gc.collect()
    if torch.cuda.is_available():
      torch.cuda.empty_cache()

    return {"status": "success", "message": "AI memory cleared for: __TEMP__"}

  def unregister_student(self, student_id: str) -> StudentMutationResponse:
    face_db = self._face_store.load()
    if student_id not in face_db:
      return {"status": "error", "message": f"Student {student_id} is not registered."}

    embeddings: list[Tensor] = face_db.pop(student_id)
    for embedding in embeddings:
      del embedding

    self._face_store.save(face_db)
    gc.collect()
    if torch.cuda.is_available():
      torch.cuda.empty_cache()

    return {"status": "success", "message": f"Student {student_id} was unregistered."}

  def _load_image(self, image_bytes: bytes) -> Optional[ImageType]:
    try:
      return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
      return None

  def _find_best_match(self, face_db: FaceDatabase, current_embedding: Tensor) -> tuple[str, float]:
    best_match = ""
    best_distance = 1.0
    for student_key, embeddings in face_db.items():
      for saved_embedding in embeddings:
        distance = (saved_embedding - current_embedding).norm().item()
        if distance < 0.8 and distance < best_distance:
          best_distance = distance
          best_match = student_key
    return best_match, best_distance
