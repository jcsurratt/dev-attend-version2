# Dev Attend Walkthrough

## What This App Does

This project is a web application for attendance.

It has two main jobs:

- show web pages for teachers and students
- connect to a PostgreSQL database to read and save student data

It also has face recognition code for camera-based attendance, but that part is more advanced and is kept in its own service so the rest of the app stays easier to understand.

## Big Picture

Think of the app like a small school office:

- one person opens the building
- one person directs visitors to the right room
- one person talks to the database
- one person handles face recognition

In this project, different files do those different jobs.

## Main Folder Layout

The important code is in `pythonServer/`.

Inside that folder:

- `main.py` starts the app
- `app/__init__.py` builds the FastAPI application
- `app/settings.py` reads configuration from `.env`
- `app/db.py` opens database connections
- `app/routes/` holds the URL endpoints
- `app/repositories/` holds database queries
- `app/services/` holds special business logic such as face recognition

## Step 1: Starting The App

File:

- `pythonServer/main.py`

This file is very small on purpose.

It only does this:

1. import the function that builds the app
2. create the app object

That is good design because it keeps the startup file simple.

## Step 2: Building The App

File:

- `pythonServer/app/__init__.py`

This file creates the FastAPI app.

It also does three important things:

1. adds the page routes
2. adds the API routes
3. mounts the static folders

Static folders are things like:

- HTML files
- CSS files
- JavaScript files
- images

When the browser asks for `/static/style.css`, FastAPI knows where to find it because of this setup.

## Step 3: Reading Settings From `.env`

File:

- `pythonServer/app/settings.py`

This file reads values from the `.env` file.

Examples:

- database host
- database port
- database name
- database username
- database password

Why this matters:

- we do not want passwords hardcoded in the source code
- different computers may use different database settings

The `Settings` class acts like a container for configuration values.

## Step 4: Connecting To The Database

File:

- `pythonServer/app/db.py`

This file is responsible for opening a connection to PostgreSQL.

It uses the settings from `.env` and creates a connection only when needed.

This is better than putting database code directly in every route.

Why:

- less repeated code
- easier to update later
- easier to debug

Important note:

`POSTGRES_HOST` is the database host, not the web site host. If the app pages
load but classes, students, or camera registration do not initialize, check the
API routes such as `/api/classes` and `/api/students`. If those requests hang
or return an error, the backend may be waiting on a database connection. In the
shared classroom setup, PostgreSQL should use `POSTGRES_HOST=192.168.1.65`.

To let other devices reach the web app, start Uvicorn with `--host 0.0.0.0`
and use the computer's LAN IP address in the browser. That changes where the web
server listens; it does not change where the database lives.

For the current classroom database, this computer was placed on the same subnet
with `192.168.1.66/24`, and PostgreSQL is reached at `192.168.1.65:5432`. If
the computer only has a `169.254.x.x` address, it cannot reach that database.

## Step 5: Repositories Talk To The Database

Files:

- `pythonServer/app/repositories/roster.py`
- `pythonServer/app/repositories/attendance.py`

A repository is a file whose job is to talk to the database.

You can think of a repository as the "database helper" part of the app.

### `roster.py`

This file handles student-related database work.

Examples:

- get all students
- get one student's name
- add a new student
- check whether a student exists
- test whether the database is working

### `attendance.py`

This file handles attendance-related database work.

Right now it has a function for getting attendance records between two dates.

It also includes compatibility behavior for the shared `192.168.1.65` database:

- if `roster` does not have a class-assignment column, automatic absence marking skips instead of crashing
- if `stu_attend` has `attend_timestamp`, the app adds/backfills the expected `timestamp` column

These checks let the app work against both the classroom database and newer local schemas.

## Step 6: Routes Handle Web Requests

Files:

- `pythonServer/app/routes/pages.py`
- `pythonServer/app/routes/api.py`

Routes are the URLs the browser can visit.

For example:

- `/`
- `/teacher`
- `/roster`
- `/api/students`

### `pages.py`

This file returns HTML pages.

Examples:

- landing page
- camera page
- roster page
- attendance page
- teacher dashboard

These routes mostly send back files such as `index.html`.

### `api.py`

This file returns data.

Usually that data is JSON.

Examples:

- `/api/testdb`
- `/api/students`
- `/api/addStudents`
- `/api/getUserName`

This file does not usually write SQL directly.
Instead, it calls repository functions.

That is a good pattern because:

- routes stay short
- database logic stays in one place

## Step 7: How A Normal Request Flows

Here is an easy example using `/api/students`.

1. The browser sends a request to `/api/students`.
2. FastAPI matches that URL to a function in `routes/api.py`.
3. That route calls a function in `repositories/roster.py`.
4. The repository opens a database connection using `db.py`.
5. PostgreSQL sends back the student rows.
6. The repository returns the data.
7. The route sends the data back to the browser as JSON.

That is the basic pattern for most API endpoints.

## Step 8: Face Recognition Is Kept Separate

Files:

- `pythonServer/app/services/face_recognition.py`
- `pythonServer/app/services/face_store.py`

These files are more advanced, so they were moved into a `services` folder.

### `face_store.py`

This file loads and saves face data from a file.

It does not use PostgreSQL right now.

That was a project decision during the refactor.

### `face_recognition.py`

This file handles:

- loading the AI face models
- turning images into face embeddings
- comparing faces
- clearing temporary face data

This code is separated from routes because it is specialized logic.

That keeps the route files simpler and easier to read.

The camera page also loads `/api/classes` before starting camera recognition.
That prevents the class dropdown from appearing blank because of the internal
`__all__` value used by the JavaScript state.

## Step 9: The Frontend Files

Frontend files are in:

- `pythonServer/studentUI/`

These are the files the browser uses directly.

Examples:

- `landing/index.html`
- `teacher/index.html`
- `roster/app.js`
- `camera/app.js`
- `style.css`

### HTML

HTML builds the structure of the page.

Examples:

- buttons
- headers
- layout

### CSS

CSS controls the look of the page.

Examples:

- colors
- spacing
- fonts

### JavaScript

JavaScript makes the page interactive.

Examples:

- calling the API
- updating the screen
- reacting to button clicks

## Step 10: Example Of A Write Request

Here is what happens when a new student is added.

1. The browser sends a POST request to `/api/addStudents`.
2. The route in `routes/api.py` receives `fname` and `lname`.
3. The route calls `add_student()` in `repositories/roster.py`.
4. That function runs an `INSERT` query in PostgreSQL.
5. PostgreSQL creates the row and returns the new student ID.
6. The route sends that result back to the browser.

This is a clean and easy-to-follow design because each file has one main job.

## Why The Refactor Helped

Before the refactor, many jobs were mixed into one large file.

That made the project harder to understand.

Now the code is easier to read because:

- startup is in one place
- settings are in one place
- database code is in one place
- routes are in one place
- face logic is in one place

This is called separation of concerns.

That phrase sounds fancy, but it just means:

"Put each kind of work in the file where it belongs."

## Good Beginner Mental Model

If you are new to programming, try thinking about the app like this:

- `main.py` = turn the app on
- `__init__.py` = put the app together
- `settings.py` = read the app's settings
- `db.py` = open the database door
- `repositories/` = ask the database questions
- `routes/` = answer web requests
- `services/` = handle special logic
- `studentUI/` = what the user sees in the browser

## If You Want To Explore The Code

Start in this order:

1. `pythonServer/main.py`
2. `pythonServer/app/__init__.py`
3. `pythonServer/app/routes/pages.py`
4. `pythonServer/app/routes/api.py`
5. `pythonServer/app/repositories/roster.py`
6. `pythonServer/app/db.py`
7. `pythonServer/app/settings.py`

After that, move into the face recognition files if you want the advanced part.

## Final Summary

This app works by:

- starting FastAPI
- loading settings from `.env`
- connecting to PostgreSQL when needed
- sending page requests to page routes
- sending data requests to API routes
- using repositories for database work
- using services for specialized logic

That structure makes the project much easier to learn, maintain, and improve.
