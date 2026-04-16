# Dev Attend

Dev Attend is a classroom attendance application.

Its main purpose is to help manage a student roster and support attendance workflows through a web app. It also includes a camera-based face recognition feature that can be used for student registration and attendance tracking.

## What The App Does

This project gives you a simple attendance system with:

- a home page that explains the system
- a teacher dashboard
- a roster page for viewing and adding students
- an attendance page
- a camera page for face-based registration and recognition
- a connection to a PostgreSQL database for student data

In simple terms, this app is meant to help an instructor:

- keep a list of students
- look up student names
- add new students
- view attendance-related information
- use a camera workflow for face recognition features

## Main Parts Of The App

There are two big sides to the project:

### 1. The pages people see in the browser

These include:

- Home
- Teacher Dashboard
- Roster
- Attendance
- Camera

These pages are built from HTML, CSS, and JavaScript files inside `pythonServer/studentUI/`.

### 2. The backend that does the work

The backend:

- starts the application
- reads settings from `.env`
- connects to PostgreSQL
- responds to API requests
- handles face-recognition logic

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
  requirements.txt
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

Right now, the app successfully connects to PostgreSQL and the student-related routes are working.

The app expects database connection values in `.env`.

Important values:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

Optional value:

- `FACE_DB_PATH`

## Environment File

Create a `.env` file in the project root. You can start from `.env.example`.

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

This project uses a Python virtual environment.

On this machine, the safest way to use it is to call the virtual environment's Python directly instead of relying on shell activation.

### 1. Create the virtual environment

```powershell
py -3.9 -m venv .venv
```

### 2. Optional: activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation does not work on your machine, that is okay. You can still run everything by calling `.\.venv\Scripts\python.exe` directly.

### 3. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Start the app

```powershell
.\.venv\Scripts\python.exe -m uvicorn pythonServer.main:app --reload
```

Then open:

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

## Important Notes

- Google authentication has been removed from this version.
- The app does not require login right now.
- Face data is still stored in a file-based face database.
- Student and roster information comes from PostgreSQL.
- The attendance endpoint depends on the correct attendance table existing in PostgreSQL.

## Documents In This Repo

Helpful files:

- `walkthrough.md` for an easy explanation of how the code works
- `refactor.md` for the refactor plan and design direction

## Summary

Dev Attend is a classroom attendance web app.

It is designed to help manage students, support attendance workflows, and provide a camera-based face recognition feature. The project now has a cleaner backend structure, a simpler setup process, and a PostgreSQL-based data connection with no login required in the current version.
