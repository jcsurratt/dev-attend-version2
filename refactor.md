# Refactor Plan

## Goals

This project needs a full structural refactor rather than a series of small fixes. The current application works from a single large server file with mixed responsibilities, hardcoded secrets, dead code, duplicate routes, and partial authentication logic. The goal of this refactor is to make the application easier to run, safer to configure, and much easier to maintain.

## Confirmed Decisions

- Keep PostgreSQL as the system of record.
- Remove Google authentication entirely.
- Do not replace Google auth with any other auth yet.
- Remove wrapper scripts such as `.cmd` and `.sh` files.
- Use a standard Python virtual environment created with `venv`.
- Move database connection logic into its own module.
- Use a `.env` file where configuration belongs.
- Keep face embedding storage out of PostgreSQL for now.

## Problems In The Current Project

### 1. Application structure is too tightly coupled

`pythonServer/main.py` currently combines:

- app creation
- middleware setup
- secrets loading
- Google auth
- session handling
- PostgreSQL connection setup
- roster queries
- attendance queries
- face recognition model setup
- face embedding persistence
- route definitions
- static file mounting

This makes the application hard to test, hard to debug, and risky to change.

### 2. Secrets and settings are mixed into source code

The current code includes hardcoded database credentials, a hardcoded session secret, and secret lookup logic tied to SOPS. That is not a good fit for a simpler local development workflow. Runtime configuration should come from environment variables, loaded from a `.env` file for local development.

### 3. Authentication is unfinished and currently not needed

Google OAuth is wired into both backend and frontend, but the project no longer needs auth at this stage. Removing it now will simplify the code and avoid carrying around broken or partially enforced access checks.

### 4. Database access is not isolated

The current code opens a global PostgreSQL connection and cursor in the main module and uses them directly in routes. That creates poor separation of concerns and makes it harder to manage errors, transactions, and future changes.

### 5. Face embeddings are stored separately from PostgreSQL

The project currently stores recognition embeddings in `face_db.pkl`. You do not want to move that data into PostgreSQL during this refactor, so the right goal is to isolate the file-based storage behind a clean module boundary. That will make the current approach easier to maintain now and easier to replace later if needed.

### 6. Repo contains student workflow scripts that are not part of the app

The `.cmd` and `.sh` files in the repository are mostly local helper scripts for git workflow, setup, and startup. They are not part of the actual application and add noise to the project. The project should be runnable with documented Python commands instead.

## Refactor Plan

### Phase 1: Establish a clean application foundation

- Create a clear module structure for app setup, configuration, routes, services, and database access.
- Split the current monolithic `main.py` into smaller files with focused responsibilities.
- Keep the initial behavior as close as practical while improving structure.

Why:
This gives us a stable base before changing storage and route behavior.

### Phase 2: Introduce environment-based configuration

- Add a `.env.example` file documenting required variables.
- Load configuration from environment variables.
- Remove hardcoded PostgreSQL credentials from source code.
- Remove secret-loading behavior that is no longer needed for this version.

Why:
Configuration should be external to the codebase so the app can run cleanly across environments.

### Phase 3: Isolate PostgreSQL access

- Move connection creation into a dedicated database module.
- Replace direct global cursor usage with helper functions or repository-style access.
- Centralize database queries for roster, attendance, and face data.

Why:
This makes the application safer, easier to test, and easier to evolve.

### Phase 4: Remove authentication

- Delete Google OAuth routes and related dependencies.
- Remove session-based auth middleware if it is no longer needed.
- Remove login/logout UI elements and any fake client-side auth placeholders.
- Make current instructor/admin pages accessible without auth for now.

Why:
The project does not need auth in this version, and removing it reduces complexity immediately.

### Phase 5: Isolate face embedding storage cleanly

- Move face embedding read/write logic out of `main.py` into its own service or storage module.
- Keep the current file-based approach temporarily, but make it configurable and easier to replace later.
- Make sure face storage is no longer mixed directly with route logic.

Why:
This reduces coupling now without forcing a storage redesign you do not want in this refactor.

### Phase 6: Remove unnecessary scripts and update developer workflow

- Delete root-level `.cmd` and `.sh` wrapper scripts that are not needed.
- Replace setup instructions with a small documented `venv` workflow.
- Update `readme.md` so the project can be installed and run with standard commands.

Why:
The repository should be understandable without custom wrapper tooling.

### Phase 7: Cleanup and verification

- Remove unused dependencies from `requirements.txt`.
- Update imports and route references after file moves.
- Run the app locally and verify key flows:
  - landing page
  - camera page
  - attendance page
  - roster page
  - add student flow
  - attendance queries
  - face registration
  - face recognition

Why:
A refactor only helps if the resulting app still works.

## Expected New Structure

The exact names may shift slightly during implementation, but the project should move toward something like this:

```text
pythonServer/
  main.py
  app/
    config.py
    db.py
    repositories/
      roster.py
      attendance.py
    routes/
      pages.py
      api.py
    services/
      face_recognition.py
      face_store.py
```

## Environment Variables To Add Later

When I reach the configuration step, I will ask you to provide values for the `.env` file. I expect we will need at least:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

We may also add app-specific values such as host, port, or debug mode if needed.

## Notes On Scope

This refactor is focused on code structure, configuration, storage cleanup, and removal of auth/script clutter. It is not yet intended to redesign the UI or introduce a new authentication system. Those can happen in later iterations once the foundation is stable.

## Definition Of Done

The refactor will be considered successful when:

- the app no longer depends on Google auth
- the app no longer uses wrapper scripts
- configuration is pulled from environment variables
- PostgreSQL connection logic is isolated
- face embedding storage is isolated from route code
- the main server file is broken into maintainable modules
- the app can be started with a standard `venv`-based Python workflow
- key pages and API flows still function
