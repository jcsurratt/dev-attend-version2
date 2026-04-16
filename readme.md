# Dev Attend

Dev Attend is a classroom attendance application.

It is built to help a student development team understand and extend a real web application that manages rosters, supports attendance workflows, and includes a camera-based face recognition feature for registration and attendance tracking.

The backend uses FastAPI, student and attendance data live in PostgreSQL, and face embeddings are stored locally in a file-based face database.

## What The App Does

The project currently includes:

- a home page that explains the system
- a teacher dashboard
- a roster page for viewing and adding students
- an attendance page
- a camera page for face-based registration and recognition
- a connection to a PostgreSQL database for student data

In practice, the app is meant to help an instructor:

- keep a list of students
- look up student names
- add new students
- view attendance-related information
- use a camera workflow for face recognition features

## Main Parts Of The App

When you are learning or contributing to the project, it helps to think of it in two main parts:

### 1. The browser-based interface

These include:

- Home
- Teacher Dashboard
- Roster
- Attendance
- Camera

These pages are built from HTML, CSS, and JavaScript files inside `pythonServer/studentUI/`.

### 2. The backend application

The backend is responsible for:

- starting the application
- reading settings from `.env`
- connecting to PostgreSQL
- responding to API requests
- handling face-recognition logic
- caching model files locally in `.torch-cache`

The backend code lives in `pythonServer/`.

## Current Features

### Pages

- landing page at `/`
- dashboard page at `/teacher`
- roster page at `/roster`
- attendance page at `/attendance`
- camera page at `/camera`

### Student And Database Features

- test the database connection
- list students
- add students
- look up a student's full name by ID
- request attendance records by date range

### Face Recognition Features

- register a student face from an uploaded image
- recognize faces from camera frames
- clear temporary face data used during registration

## Project Structure

The important project folders and files are:

```text
dev-attend2/
  pythonServer/
    main.py
    app/
      __init__.py
      settings.py
      db.py
      repositories/
        roster.py
        attendance.py
      routes/
        pages.py
        api.py
      services/
        face_store.py
        face_recognition.py
    studentUI/
      landing/
      teacher/
      roster/
      attendance/
      camera/
      style.css
      navbar.js
  .env
  .env.example
  .torch-cache/
  requirements.txt
  topology-diagram.md
  adding a new feature.md
  walkthrough.md
  refactor.md
```

## How The App Works

At a high level:

1. The app starts in `pythonServer/main.py`.
2. It builds the FastAPI application.
3. It reads database settings from `.env`.
4. It serves web pages to the browser.
5. It uses API routes to talk to the database.
6. It uses service files for face recognition work.

If you want a more detailed beginner-friendly explanation, read:

- `walkthrough.md`

## Database

This project uses PostgreSQL.

The app is designed to connect to PostgreSQL for roster and attendance data.

The app expects database connection values in `.env`.

These PostgreSQL settings are required. The app does not fall back to hardcoded database credentials in source code.

Important values:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

Optional value:

- `FACE_DB_PATH`

The face-recognition model weights are cached locally in `.torch-cache/` after they are downloaded. That directory is only for local runtime use and should not be committed to GitHub.

## Environment File

Create a `.env` file in the project root. You can start from `.env.example`.

If a required PostgreSQL value is missing or blank, the app will fail at startup with a clear configuration error.

Example:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=dev-attend
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
FACE_DB_PATH=face_db.pkl
```

## Local Setup

These steps are written for a student team working from their own development environments. The exact shell behavior may vary a little from machine to machine, but the overall workflow should stay the same.

This project uses a Python virtual environment.

For consistency across a student team, it is usually best to call the virtual environment's Python directly instead of depending on shell activation behavior.

### 1. Create the virtual environment

```powershell
py -3.9 -m venv .venv
```

### 2. Optional: activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation is not available or behaves differently in your shell, you can still run everything by calling `.\.venv\Scripts\python.exe` directly.

### 3. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Start the app

```powershell
.\.venv\Scripts\python.exe -m uvicorn pythonServer.main:app --reload
```

After the server starts, open:

- `http://127.0.0.1:8000`

## Current Routes

### Pages

- `/`
- `/teacher`
- `/roster`
- `/attendance`
- `/camera`

### API

- `/api/testdb`
- `/api/students`
- `/api/addStudents`
- `/api/getUserName`
- `/api/sql/attendanceByDay`
- `/api/recognizeFrame`
- `/registerStudent`
- `/delTempFace`

## Team Notes

- Google authentication has been removed from this version.
- The app does not require login in its current form.
- Face data is still stored in a file-based face database.
- Face-recognition model files are cached locally in `.torch-cache`.
- Student and roster information comes from PostgreSQL.
- The attendance endpoint depends on the correct attendance table existing in PostgreSQL.
- For team work, keep secrets in `.env`, keep local caches out of Git, and document any new feature flow you add.

## Documents In This Repo

Helpful files:

- `walkthrough.md` for an easy explanation of how the code works
- `refactor.md` for the refactor plan and design direction
- `topology-diagram.md` for a visual architecture overview
- `adding a new feature.md` for step-by-step feature planning guidance

## Summary

Dev Attend is a classroom attendance web app.

It is a good team project for learning how frontend code, API routes, SQL, configuration, and face-recognition workflows fit together in one application. The project has a clear backend structure, a straightforward setup process, and documentation to help new contributors understand both the architecture and the feature-development workflow.
