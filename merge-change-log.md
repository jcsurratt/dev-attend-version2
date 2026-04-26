# Merge Change Log

This change log explains the work that was merged into the safe integration branch:

`codex/merge-active-branches`

The goal of this merge was to bring together the student branches that had active work without losing anyone's changes.

## Branches included

- `T1-51`
- `t1-51-database-update`
- `codex-attendance-database-sync`

Some other branches were already included in `main` before this merge, so they did not need separate merge work:

- `live-updates`
- `dj-site-ui-update-4172026`
- `codex-camera-registration-roster-updates`

## New features and improvements

### Attendance export by class

Teachers can now export attendance records for a selected class as a CSV file.

This is useful when attendance data needs to be opened in Excel, shared, archived, or uploaded somewhere else.

What changed:

- Added an attendance export button to the attendance page.
- The export button stays disabled until a class is selected.
- Added a backend export endpoint for class attendance.
- The exported CSV includes attendance information for the chosen class.

### Class-based roster filtering

The roster and attendance screens now work better with class selections.

What changed:

- Students can be filtered by class.
- Attendance can be viewed and managed for a selected class instead of mixing everyone together.
- The attendance page now asks the user to choose a class before loading students.
- Class search and class selection were improved so it is easier to find the right class.

### CSV roster import

Roster data can now be imported from a CSV file.

What changed:

- Added a CSV import endpoint for student roster data.
- Added sample test data in `test-data/roster-import-sample.csv`.
- Improved roster repository code so bulk student imports can be saved to the database.

### Attendance database sync fixes

Several branches changed how attendance data connects to the database. The merge brings those fixes together.

What changed:

- Attendance records now stay better connected to students and classes.
- Attendance logic handles class names and student IDs more consistently.
- Attendance records can be marked present, absent, late, excused, or changed manually.
- The system can mark absences for students who have not checked in.
- Attendance data is serialized in a consistent format for the frontend.

### Class schedule support

Classes now have more schedule-aware behavior.

What changed:

- Class schedule details can be stored and updated.
- The system can use meeting days and meeting times to help determine attendance status.
- Class details are pulled from the database when available.

### Roster and camera registration cleanup

The merge keeps earlier improvements from `main` and combines them with the roster updates.

What changed:

- Roster-created and camera-created students are handled more consistently.
- Student names and class assignments can be updated.
- Students can be removed from the roster.
- Camera registration can create placeholder student records for a selected class.

## Important merge note

There was one conflict while merging `codex-attendance-database-sync`.

The conflict was in:

`pythonServer/studentUI/attendance/app.js`

The conflict was caused by two different versions of the class selection behavior:

- One version used `"All Students"` as the default class.
- The newer combined version uses an empty selection and asks the user to choose a class.

The merge kept the newer behavior because it works better with class-specific attendance and export.

## Validation performed

After the merge, these checks passed:

- Python files parsed successfully.
- The FastAPI app imported successfully.
- Attendance JavaScript passed a syntax check.
- Roster JavaScript passed a syntax check.

There are no full automated app tests in this repository yet, so the next best step is manual testing in the browser.

## Suggested manual testing

Before considering the merge complete, test these workflows:

1. Open the app and confirm the main pages load.
2. Create or select a class.
3. Add a student to a class.
4. Import students from a CSV file.
5. Open the attendance page and choose a class.
6. Mark a student present.
7. Change a student's attendance status.
8. Export attendance for a selected class.
9. Confirm the exported CSV opens correctly.
10. Confirm camera registration still works for a selected class.

## Summary

This merge mainly adds class-focused attendance workflows:

- Better class selection
- Roster filtering by class
- CSV roster import
- Attendance export
- Attendance database sync fixes
- Schedule-aware attendance behavior

The safe integration branch is ready for GitHub review before merging into `main`.
