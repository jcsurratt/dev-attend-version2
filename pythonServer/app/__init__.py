from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes.api import router as api_router
from .routes.pages import router as pages_router
from .settings import get_settings


def create_app() -> FastAPI:
  settings = get_settings()

  app = FastAPI(title="Dev Attend")
  app.include_router(pages_router)
  app.include_router(api_router)
  app.mount(
    "/jsGlobals",
    StaticFiles(directory=str(settings.js_globals_dir)),
    name="jsGlobals",
  )
  app.mount(
    "/static",
    StaticFiles(directory=str(settings.static_dir)),
    name="static",
  )
  return app
