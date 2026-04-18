let currentClass = "All Students"
let availableClasses = []
const studentsDiv = document.getElementById("students")
const classSelect = document.getElementById("classSelect")
const classSearchInput = document.getElementById("classSearchInput")
const classSearchResults = document.getElementById("classSearchResults")
const ATTENDANCE_REFRESH_MS = 5000
let studentRenderRequestId = 0
let renderedStudentSignature = ""

function getSelectedClass() {
  if (!classSelect.options.length) return ""
  return classSelect.value || "All Students"
}

async function loadClasses(preferredClass = null) {
  const data = await (await fetch("/api/classes")).json()
  availableClasses = data.classes || []
  renderClassOptions(preferredClass)
}

function renderClassOptions(preferredClass = null) {
  const classSearch = classSearchInput.value.toLowerCase().trim()
  const matchingClasses = availableClasses.filter((classOption) =>
    classOption.label.toLowerCase().includes(classSearch),
  )
  classSelect.innerHTML = ""

  for (const classOption of availableClasses) {
    const option = document.createElement("option")
    option.value = classOption.value
    option.textContent = classOption.label
    classSelect.appendChild(option)
  }

  if (!classSelect.options.length) {
    renderClassSearchResults(matchingClasses, classSearch)
    return
  }

  const matchingClass =
    Array.from(classSelect.options).find(
      (option) => option.value === preferredClass,
    )?.value || classSelect.options[0].value

  classSelect.value = matchingClass
  currentClass = matchingClass
  renderClassSearchResults(matchingClasses, classSearch)
}

function renderClassSearchResults(classes, classSearch) {
  classSearchResults.innerHTML = ""

  const resultCountText =
    classes.length === 1 ? "1 matching class" : `${classes.length} matching classes`
  classSearchResults.appendChild(
    newElement("div", { class: "class-search-summary" }, [
      classSearch ? resultCountText : "Showing all classes",
    ]),
  )

  if (!classes.length) {
    classSearchResults.appendChild(
      newElement("div", { class: "class-search-empty" }, [
        `No classes match "${classSearchInput.value.trim()}".`,
      ]),
    )
    return
  }

  for (const classOption of classes) {
    const button = newElement(
      "button",
      {
        class:
          classOption.value === currentClass ?
            "class-result selected"
          : "class-result",
        type: "button",
      },
      [classOption.label],
    )
    button.addEventListener("click", async () => {
      classSelect.value = classOption.value
      currentClass = classOption.value
      classSearchInput.value = classOption.label
      renderClassOptions(classOption.value)
      await renderStudents()
    })
    classSearchResults.appendChild(button)
  }
}

function newElement(tagName, attrs = {}, children = []) {
  const element = document.createElement(tagName)
  Object.entries(attrs).forEach(([key, value]) => {
    element.setAttribute(key, value)
  })
  children.forEach((child) => element.append(child))
  return element
}

function formatAttendanceLabel(attendance) {
  if (!attendance || !attendance.status) return "Attendance:"
  const status = attendance.status.charAt(0).toUpperCase() + attendance.status.slice(1)
  const manual = attendance.manual_override ? " Manually Updated." : ""
  return `Attendance: ${status}.${manual}`
}

function applyAttendanceDisplay(container, attendance) {
  const label = container.querySelector(".attendance-status")
  const select = container.querySelector(".attendance-status-select")
  if (!label || !select) return
  label.textContent = formatAttendanceLabel(attendance)
  label.className = `attendance-status ${attendance?.status || "not-marked"}`
  select.value = attendance?.status || "not_marked"
  select.classList.toggle("not-marked", !attendance?.status)
}

async function updateStudentAttendance(student, container) {
  const statusSelect = container.querySelector(".attendance-status-select")
  const formData = new FormData()
  formData.append("studentId", student.id)
  formData.append("studentName", student.name)
  formData.append("class_name", student.class_name || getSelectedClass() || "All Students")
  formData.append("status", statusSelect.value)

  const data = await (
    await fetch("/api/attendance/updateStatus", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to update attendance.")
    return
  }

  student.attendance = data.attendance
  applyAttendanceDisplay(container, data.attendance)
}

function createAttendanceControl(student, container) {
  if ((student.class_name || getSelectedClass()) === "All Students") {
    return newElement("div", { class: "attendance-control" }, [
      newElement("span", { class: "attendance-status not-marked" }, ["Attendance:"]),
      newElement("span", { class: "attendance-na-label" }, ["N/A"]),
    ])
  }

  const statusLabel = newElement("span", { class: "attendance-status" }, [])
  const select = newElement("select", {
    class: "attendance-status-select",
    "aria-label": "Attendance Status",
  }, [
    newElement("option", { value: "not_marked", disabled: "disabled" }, ["Not Marked"]),
    newElement("option", { value: "present" }, ["Present"]),
    newElement("option", { value: "tardy" }, ["Tardy"]),
    newElement("option", { value: "absent" }, ["Absent"]),
  ])
  select.addEventListener("change", () => updateStudentAttendance(student, container))

  const control = newElement("div", { class: "attendance-control" }, [
    statusLabel,
    select,
  ])
  applyAttendanceDisplay(control, student.attendance)
  return control
}

function updateExistingStudentRows(students) {
  for (const student of students) {
    const row = studentsDiv.querySelector(`[data-student-id="${student.id}"]`)
    if (!row) continue

    row.dataset.studentName = student.name
    row.dataset.className = student.class_name || getSelectedClass()
    row.querySelector(".attendance-student-name").textContent = student.name
    applyAttendanceDisplay(row, student.attendance)

    const classSelectControl = row.querySelector(".student-class-select")
    if (classSelectControl && classSelectControl.value !== student.class_name) {
      classSelectControl.value = student.class_name || getSelectedClass()
    }
  }
  searchStudents()
}

async function renderStudents() {
  const requestId = ++studentRenderRequestId
  const selectedClass = getSelectedClass()
  if (!selectedClass) return
  const encodedClass = encodeURIComponent(selectedClass)
  const students = await (
    await fetch(`/api/classStudents?class_name=${encodedClass}`)
  ).json()
  if (requestId !== studentRenderRequestId) return

  const nextSignature = JSON.stringify(
    students.map((student) => [
      student.id,
      student.name,
      student.class_name,
    ]),
  )
  if (nextSignature === renderedStudentSignature) {
    updateExistingStudentRows(students)
    return
  }
  renderedStudentSignature = nextSignature

  const fragment = document.createDocumentFragment()
  students.forEach((student) => {
    const div = newElement("div", {
      class: "student attendance-student",
      "data-student-id": student.id,
      "data-student-name": student.name,
      "data-class-name": student.class_name || selectedClass,
    }, [
      newElement("span", { class: "attendance-student-name" }, [student.name]),
      newElement("div", { class: "student-attendance" }, []),
      newElement("div", { class: "student-class-control" }, [
        newElement("span", { class: "class-change-label" }, ["Change Class:"]),
        createStudentClassSelect(student.id, student.class_name || selectedClass),
      ]),
    ])
    div.querySelector(".student-attendance").appendChild(createAttendanceControl(student, div))
    fragment.appendChild(div)
  })
  studentsDiv.replaceChildren(fragment)
  searchStudents()
}

function createStudentClassSelect(studentId, selectedClass) {
  const select = newElement(
    "select",
    { class: "student-class-select", "aria-label": "Student Class" },
    [],
  )

  for (const classOption of availableClasses) {
    const option = document.createElement("option")
    option.value = classOption.value
    option.textContent = classOption.label
    option.selected = classOption.value === selectedClass
    select.appendChild(option)
  }

  select.addEventListener("change", async () => {
    await updateStudentClass(studentId, select.value)
  })
  return select
}

async function updateStudentClass(studentId, className) {
  const formData = new FormData()
  formData.append("studentId", studentId)
  formData.append("class_name", className)

  const data = await (
    await fetch("/api/students/updateClass", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to update student class.")
    renderedStudentSignature = ""
    await renderStudents()
    return
  }

  await loadClasses(currentClass)
  renderedStudentSignature = ""
  await renderStudents()
}

window.addStudent = async function () {
  const firstNameInput = document.getElementById("newStudentFirstName")
  const lastNameInput = document.getElementById("newStudentLastName")
  const fname = firstNameInput.value.trim()
  const lname = lastNameInput.value.trim()
  if (!fname && !lname) return

  const formData = new FormData()
  formData.append("fname", fname)
  formData.append("lname", lname)
  formData.append("class_name", getSelectedClass())

  const data = await (
    await fetch("/api/addStudents", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to add student.")
    return
  }

  firstNameInput.value = ""
  lastNameInput.value = ""
  renderedStudentSignature = ""
  await renderStudents()
}

window.searchStudents = function () {
  const filter = document.getElementById("searchInput").value.toLowerCase()
  document.querySelectorAll(".student").forEach((div) => {
    div.style.display =
      div.textContent.toLowerCase().includes(filter) ? "" : "none"
  })
}

window.searchClasses = async function () {
  renderClassOptions(currentClass)
}

classSelect.addEventListener("change", async function () {
  currentClass = getSelectedClass()
  renderedStudentSignature = ""
  await renderStudents()
})

;(async () => {
  await loadClasses("All Students")
  await renderStudents()
  setInterval(renderStudents, ATTENDANCE_REFRESH_MS)
})()
