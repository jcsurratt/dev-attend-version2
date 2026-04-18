from pathlib import Path

from fastapi import APIRouter
from starlette.responses import FileResponse, RedirectResponse

from pythonServer.app.settings import get_settings


router = APIRouter()
settings = get_settings()


def _page(relative_path: str) -> FileResponse:
  return FileResponse(
    Path(settings.static_dir, relative_path),
    headers={
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      "Pragma": "no-cache",
      "Expires": "0",
    },
  )


@router.api_route("/", methods=["GET", "HEAD"])
def landing_page() -> FileResponse:
  return _page("landing/index.html")


@router.api_route("/camera", methods=["GET", "HEAD"])
def camera_page() -> FileResponse:
  return _page("camera/index.html")


@router.api_route("/attendance", methods=["GET", "HEAD"])
def attendance_page() -> FileResponse:
  return _page("attendance/index.html")


@router.api_route("/roster", methods=["GET", "HEAD"])
def roster_page() -> FileResponse:
  return _page("roster/index.html")


@router.api_route("/teacher", methods=["GET", "HEAD"])
def teacher_page() -> FileResponse:
  return _page("teacher/index.html")


@router.api_route("/studentPage", methods=["GET", "HEAD"])
def student_page_alias() -> RedirectResponse:
  return RedirectResponse(url="/roster")
