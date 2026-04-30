# Adding A New Feature

This guide explains how a junior programmer can add a new feature to this project.

We will use this example scenario:

## Scenario

An instructor wants a button on the attendance page that lets them manually mark a student as present.

That means we need to:

- add a user interface control
- send a request from the browser to the backend
- create a backend endpoint
- add SQL logic in the repository layer
- store the attendance record in PostgreSQL
- return a response the browser can use

This document is written as a step-by-step plan you can follow for similar features.

## Step 1: Understand The App Layers

Before writing code, understand where each kind of code belongs in this project.

- `pythonServer/studentUI/`
  This is the frontend. It contains HTML, CSS, and JavaScript for each page.

- `pythonServer/app/routes/`
  This is where FastAPI endpoints live.

- `pythonServer/app/repositories/`
  This is where SQL queries should go.

- `pythonServer/app/services/`
  This is where business logic goes if it is more than simple database access.

- `pythonServer/app/db.py`
  This is the shared PostgreSQL connection helper.

- `pythonServer/app/settings.py`
  This loads environment-based configuration like database settings and file paths.

## Step 2: Describe The Feature In Plain Language

Before coding, write down what the feature should do.

For this example:

1. The teacher opens the attendance page.
2. They see a list of students.
3. They click a button such as `Mark Present`.
4. The browser sends the student ID and attendance date to the backend.
5. The backend writes a new attendance row into PostgreSQL.
6. The backend returns success or failure.
7. The page updates the student row so the teacher can see that the student is marked present.

If you can explain the feature clearly in plain English, the implementation will usually go more smoothly.

## Step 3: Decide Which Files Need To Change

For a manual attendance feature, you would likely update these areas:

- frontend page JavaScript:
  `pythonServer/studentUI/attendance/app.js`

- frontend page HTML:
  `pythonServer/studentUI/attendance/index.html`

- API route:
  `pythonServer/app/routes/api.py`

- repository SQL:
  `pythonServer/app/repositories/attendance.py`

You may also update:

- `readme.md`
- `walkthrough.md`
- tests, if the project later adds them

## Step 4: Check The Database Table First

Before writing Python or JavaScript, confirm the database has the table and columns needed.

For example, you may need an `attendance` table with fields like:

- `id`
- `student_id`
- `student_name`
- `status`
- `day`
- `created_at`

If the table does not support the feature yet, decide what needs to change.

Questions to ask:

- Do we already store attendance records?
- Do we need a `status` column for values like `present`, `tardy`, or `absent`?
- Should we store the student ID, student name, or both?
- Should we prevent duplicate attendance entries for the same student on the same day?

Write these decisions down before coding.

## Step 5: Plan The API Request And Response

For this feature, choose what data the frontend should send.

Example request body:

- `student_id`
- `status`
- `day`

Example success response:

```json
{
  "status": "success",
  "message": "Attendance recorded",
  "student_id": 1009
}
```

Example error response:

```json
{
  "status": "error",
  "message": "Student not found"
}
```

Planning the request and response before coding helps the frontend and backend match each other.

## Step 6: Put SQL In The Repository Layer

In this codebase, SQL should go in the repository files, not directly in route handlers.

For attendance-related SQL, use:

- `pythonServer/app/repositories/attendance.py`

That file is the right place for functions such as:

- `add_attendance_record(...)`
- `attendance_exists_for_day(...)`
- `update_attendance_status(...)`

Example structure:

```python
from pythonServer.app.db import get_db_connection


def add_attendance_record(student_id: int, student_name: str, status: str, day: str) -> int:
  with get_db_connection() as connection:
    with connection.cursor() as cursor:
      cursor.execute(
        """
        INSERT INTO attendance (student_id, student_name, status, day)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        (student_id, student_name, status, day),
      )
      attendance_id = cursor.fetchone()[0]
    connection.commit()
  return attendance_id
```

Important rule:

- keep raw SQL in repository files
- keep route files focused on HTTP request/response handling

## Step 7: Build Or Update The Endpoint In `api.py`

Once the repository function exists, create or update the FastAPI endpoint in:

- `pythonServer/app/routes/api.py`

For this feature, you might add an endpoint like:

- `POST /api/attendance/mark`

What the route should do:

1. accept form or JSON input
2. validate required fields
3. call repository functions
4. return a clear JSON response

Example shape:

```python
@router.post("/api/attendance/mark")
def mark_attendance(student_id: int = Form(...), status: str = Form(...), day: str = Form(...)):
  student = get_student_name(str(student_id))
  full_name = student["fullName"]
  attendance_id = add_attendance_record(student_id, full_name, status, day)
  return {
    "status": "success",
    "message": "Attendance recorded",
    "attendance_id": attendance_id,
  }
```

Keep route logic simple.

If the route starts getting too complicated, move shared logic into:

- a repository function if it is mostly SQL
- a service function if it is business logic

## Step 8: Update The Frontend Page

Next, connect the browser UI to the new endpoint.

For the attendance feature example, update:

- `pythonServer/studentUI/attendance/index.html`
- `pythonServer/studentUI/attendance/app.js`

Possible frontend tasks:

1. add a `Mark Present` button next to each student
2. store the student ID in the DOM
3. listen for button clicks
4. create a `fetch()` call to the new API route
5. update the page after success
6. show a helpful error message if the request fails

Example frontend flow:

```javascript
async function markPresent(studentId) {
  const formData = new FormData()
  formData.append("student_id", studentId)
  formData.append("status", "present")
  formData.append("day", new Date().toISOString().slice(0, 10))

  const response = await fetch("/api/attendance/mark", {
    method: "POST",
    body: formData,
  })

  const data = await response.json()
  if (data.status === "success") {
    console.log("Attendance saved")
  } else {
    console.error(data.message)
  }
}
```

## Step 9: Handle Validation And Edge Cases

Do not stop at the happy path.

Think through what could go wrong.

For this example:

- What if the student ID does not exist?
- What if the teacher clicks the button twice?
- What if attendance was already recorded for that student today?
- What if the database is temporarily unavailable?
- What if the browser request fails?

Decide the expected behavior for each case.

Examples:

- return an error if the student does not exist
- prevent duplicate records for the same day
- disable the button after success
- show a clear frontend error message

## Step 10: Keep Naming Clear And Consistent

Use names that match the feature.

Good examples:

- `mark_attendance`
- `add_attendance_record`
- `student_id`
- `status`
- `day`

Avoid vague names like:

- `doThing`
- `handleStuff`
- `saveData`

Clear names make the code easier for the next person to maintain.

## Step 11: Test The Feature In Small Pieces

Do not wait until the very end to test everything.

Test in this order:

1. Confirm the SQL works.
2. Confirm the repository function works.
3. Confirm the API endpoint returns the expected JSON.
4. Confirm the frontend sends the correct request.
5. Confirm the page updates correctly after success.

Useful manual tests:

1. Mark a valid student present.
2. Try an invalid student ID.
3. Try clicking the button twice.
4. Check the database table to confirm the new row was inserted correctly.
5. Reload the page and confirm the state still makes sense.

## Step 12: Update Documentation

After the feature works, update project docs.

You may need to update:

- `readme.md` if the feature changes user-visible behavior
- `walkthrough.md` if it changes how the system works
- `topology-diagram.md` if it adds a new major flow

Documentation is part of the feature, not an optional extra.

## Step 13: Review For Separation Of Concerns

Before you finish, ask these questions:

- Is SQL in the repository layer instead of the route?
- Is HTTP handling in the route instead of the repository?
- Is UI logic in the frontend instead of the backend?
- Is repeated logic extracted into a helper, repository, or service?

If the answer is no, clean that up before merging the feature.

## Step 14: A Reusable Planning Template

When adding any new feature, use this planning format:

1. Describe the user scenario.
2. List the data needed.
3. Decide which page or UI changes are required.
4. Decide which API route is needed.
5. Decide which repository function and SQL are needed.
6. Decide whether a service layer helper is needed.
7. Implement backend first or in parallel with frontend.
8. Test the backend response.
9. Connect the frontend.
10. Test edge cases.
11. Update documentation.

## Step 15: Example Mini Plan For Manual Attendance

Here is a short example plan for the manual present feature.

1. Add a `Mark Present` button to each student row on the attendance page.
2. Add a frontend function in `pythonServer/studentUI/attendance/app.js` that calls a new backend route.
3. Add a `POST /api/attendance/mark` route in `pythonServer/app/routes/api.py`.
4. Add SQL in `pythonServer/app/repositories/attendance.py` to insert or update attendance.
5. Validate the student ID before writing attendance.
6. Return success or error JSON.
7. Update the frontend row after success.
8. Test valid, invalid, and duplicate-click cases.
9. Update docs so the next developer understands the new flow.

## Final Advice

When you add a feature in this project, do not start by changing random files.

Start with:

1. the user scenario
2. the data flow
3. the right layer for each change

That approach will help you build features cleanly and make the codebase easier to maintain.
