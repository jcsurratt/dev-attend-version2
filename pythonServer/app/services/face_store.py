import pickle
from typing import cast

import torch

from pythonServer.app.settings import get_settings


FaceDatabase = dict[str, list[torch.Tensor]]


class FaceStore:
  def __init__(self) -> None:
    self._path = get_settings().face_db_path

  def load(self) -> FaceDatabase:
    if not self._path.exists():
      return {}
    with self._path.open("rb") as file:
      return cast(FaceDatabase, pickle.load(file))

  def save(self, face_db: FaceDatabase, include_temp: bool = False) -> None:
    with self._path.open("wb") as file:
      pickle.dump(
        {
          key: value
          for key, value in face_db.items()
          if include_temp or key != "__TEMP__"
        },
        file,
      )

  def registered_ids(self) -> set[str]:
    return {student_id for student_id in self.load() if student_id != "__TEMP__"}
