# Application Topology

This diagram shows how the browser UI, FastAPI backend, PostgreSQL database, and local face-recognition storage work together in `dev-attend2`.

## High-Level Topology

```mermaid
flowchart LR
    User["User in Browser"]

    subgraph Frontend["Frontend (Static UI served by FastAPI)"]
        Landing["Landing Page<br/>/"]
        Teacher["Teacher Page<br/>/teacher"]
        Roster["Roster Page<br/>/roster"]
        Attendance["Attendance Page<br/>/attendance"]
        Camera["Camera Page<br/>/camera"]
        StaticAssets["JS/CSS/Images<br/>/static/* and /jsGlobals/*"]
    end

    subgraph Backend["FastAPI App"]
        Main["pythonServer/main.py"]
        AppFactory["create_app()<br/>routes + static mounts"]
        PageRoutes["Page Routes<br/>pages.py"]
        ApiRoutes["API Routes<br/>api.py"]
    end

    subgraph Services["Application Services"]
        FaceService["FaceRecognitionService"]
        FaceStore["FaceStore<br/>face_db.pkl"]
        TorchCache["Torch Model Cache<br/>.torch-cache"]
        Repos["Repositories"]
        DBConn["DB Connection Helper"]
    end

    subgraph Data["Data Stores"]
        Postgres["Shared PostgreSQL<br/>192.168.1.65:5432<br/>roster + courses + stu_attend"]
        FaceDbFile["Local Pickle File<br/>face_db.pkl"]
        ModelFiles["Downloaded Model Weights"]
    end

    User --> Landing
    User --> Teacher
    User --> Roster
    User --> Attendance
    User --> Camera

    Landing --> StaticAssets
    Teacher --> StaticAssets
    Roster --> StaticAssets
    Attendance --> StaticAssets
    Camera --> StaticAssets

    StaticAssets --> PageRoutes
    User --> Main
    Main --> AppFactory
    AppFactory --> PageRoutes
    AppFactory --> ApiRoutes

    ApiRoutes --> Repos
    ApiRoutes --> FaceService

    Repos --> DBConn
    DBConn --> Postgres

    FaceService --> FaceStore
    FaceService --> TorchCache
    FaceStore --> FaceDbFile
    TorchCache --> ModelFiles
```

## Camera And Registration Flow

```mermaid
sequenceDiagram
    participant Browser as Camera Page in Browser
    participant FastAPI as FastAPI Routes
    participant Face as FaceRecognitionService
    participant FileDB as face_db.pkl
    participant PG as PostgreSQL

    Browser->>FastAPI: GET /camera
    FastAPI-->>Browser: camera/index.html + /static/camera/app.js

    loop live recognition
        Browser->>FastAPI: POST /api/recognizeFrame (image_file)
        FastAPI->>Face: recognize_frame(image_bytes, student_name_map)
        Face->>FileDB: load embeddings
        FastAPI->>PG: query roster names
        Face-->>FastAPI: faces[]
        FastAPI-->>Browser: JSON response
    end

    opt registration mode
        Browser->>FastAPI: GET /api/getUserName?id=...
        FastAPI->>PG: lookup student name
        FastAPI-->>Browser: fullName

        loop collect face angles
            Browser->>FastAPI: POST /registerStudent
            FastAPI->>Face: register_student_image(...)
            Face->>FileDB: save embeddings
            Face-->>FastAPI: success/error
            FastAPI-->>Browser: JSON response
        end

        Browser->>FastAPI: POST /delTempFace
        FastAPI->>Face: clear_temp_face()
        Face->>FileDB: remove __TEMP__
        FastAPI-->>Browser: JSON response
    end
```

## Responsibilities By Layer

- Browser UI: renders pages, captures webcam frames, sends `fetch()` requests, and updates attendance/registration state in the user interface.
- FastAPI page routes: serve the HTML entry points for the landing, teacher, roster, attendance, and camera pages.
- FastAPI API routes: handle roster lookups, student creation, attendance queries, frame recognition, face registration, and temp-face cleanup.
- Repository layer: isolates SQL queries for roster and attendance data.
- FaceRecognitionService: loads models, detects faces, creates embeddings, compares embeddings, and returns recognition results.
- FaceStore: persists face embeddings to the local `face_db.pkl` file.
- PostgreSQL: stores student roster data, courses, and attendance records on the shared `192.168.1.65` database.
- `.torch-cache`: stores downloaded ML model weights used by `facenet-pytorch`.

## Current Network Setup

- The active database host is `192.168.1.65`.
- This development computer is configured as `192.168.1.66/24` so it can reach the database.
- Uvicorn is run on `0.0.0.0:8001`; use `http://127.0.0.1:8001` from this computer.
- The camera page should be opened from localhost when testing on this computer so browser camera permissions work reliably.

## Shared Database Compatibility

The shared database schema is not identical to every local schema this project has used.
The current code accounts for these differences:

- `roster` may contain only `stuid`, `fname`, `lname`, and `email`, with no class-assignment column.
- `stu_attend` may contain `attend_timestamp`; the app adds and backfills `timestamp` when needed.
- Auto-absence marking skips when the roster has no class-assignment column.

## Short Narrative

1. A browser requests a page such as `/camera` or `/roster`.
2. FastAPI returns the page plus its static JavaScript, CSS, and shared assets.
3. Frontend JavaScript calls API routes for data or camera processing.
4. Data-oriented routes query PostgreSQL through repository functions.
5. Face-oriented routes call `FaceRecognitionService`, which uses local model files and the local face embedding store.
6. Results are returned as JSON for the browser to render.
