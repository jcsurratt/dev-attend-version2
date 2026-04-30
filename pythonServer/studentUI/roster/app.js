Object.assign(globalThis, console)
const a = loadlib("allfuncs")

var main = a.qs("#main")
var classSelect = a.qs("#class_name")
var classList = a.qs("#classList")
var rosterClassFilter = a.qs("#rosterClassFilter")
var addNewStudentButton = a.qs("#addNewStudent")
var addStudentStatus = a.qs("#addStudentStatus")
var rosterCsvFile = a.qs("#rosterCsvFile")
var uploadRosterCsv = a.qs("#uploadRosterCsv")
var rosterCsvHint = a.qs("#rosterCsvHint")
var rosterCsvStatus = a.qs("#rosterCsvStatus")
var addStudentStatusTimer = null
var classes = []
const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
]

function getSelectedClass() {
  return classSelect.value || ""
}

function hasAssignedClassSelection() {
  const selectedClass = getSelectedClass()
  return !!selectedClass && selectedClass !== "All Students"
}

function syncClassAssignmentState() {
  const importEnabled = hasAssignedClassSelection()
  addNewStudentButton.disabled = !importEnabled
  uploadRosterCsv.disabled = !importEnabled
  rosterCsvHint.textContent =
    importEnabled ?
      `Every student in the CSV will be added to ${getSelectedClass()}.`
    : "Choose a class code before uploading."
  if (!importEnabled) {
    setRosterCsvStatus("")
  }
}

function setRosterCsvStatus(message, isError = false) {
  rosterCsvStatus.textContent = message
  rosterCsvStatus.style.color = isError ? "#b42318" : "#166534"
}

function setAddStudentStatus(message, isError = false) {
  if (!addStudentStatus) return
  clearTimeout(addStudentStatusTimer)
  addStudentStatus.textContent = message
  addStudentStatus.style.color = isError ? "#b42318" : "#166534"
  if (!message) return
  addStudentStatusTimer = setTimeout(() => {
    addStudentStatus.textContent = ""
  }, 2500)
}

function getRosterFilterValue() {
  return rosterClassFilter.value || "__all__"
}

function populateRosterClassFilter(selectedValue = "__all__") {
  const nextValue =
    selectedValue === "__all__" || classes.some((classOption) => classOption.value === selectedValue) ?
      selectedValue
    : "__all__"

  rosterClassFilter.innerHTML = ""
  rosterClassFilter.appendChild(a.newelem("option", { value: "__all__" }, ["All classes"]))
  for (const classOption of classes) {
    rosterClassFilter.appendChild(
      a.newelem("option", { value: classOption.value }, [classOption.label]),
    )
  }
  rosterClassFilter.value = nextValue
}

function applyRosterClassFilter() {
  const selectedFilter = getRosterFilterValue()
  document.querySelectorAll(".roster-student-row").forEach((row) => {
    const rowClassName = row.dataset.className || "All Students"
    row.style.display =
      selectedFilter === "__all__" || rowClassName === selectedFilter ? ""
      : "none"
  })
}

async function loadClasses(preferredClass = null) {
  const data = await (await fetch("/api/classes")).json()
  classes = data.classes || []

  classSelect.innerHTML = ""
  classSelect.appendChild(a.newelem("option", { value: "" }, ["Choose a class code"]))
  for (const classOption of classes) {
    const option = document.createElement("option")
    option.value = classOption.value
    option.textContent = classOption.label
    classSelect.appendChild(option)
  }

  if (classSelect.options.length) {
    const selected =
      Array.from(classSelect.options).find(
        (option) => option.value === preferredClass,
      )?.value || ""
    classSelect.value = selected
  }

  renderClassList()
  updateStudentClassSelectors(preferredClass || "All Students")
  populateRosterClassFilter(getRosterFilterValue())
  syncClassAssignmentState()
  applyRosterClassFilter()
}

function renderClassList() {
  classList.innerHTML = ""
  if (!classes.length) {
    classList.appendChild(a.newelem("p", { class: "empty-state" }, ["No classes yet."]))
    return
  }

  for (const classOption of classes) {
    const className = classOption.value
    const row = a.newelem("div", { class: "class-row class-schedule-row" }, [])
    const summary =
      className === "All Students" ?
        "All Students is the default class for students currently unassigned to a proper class."
      : formatScheduleSummary(classOption)
    const details = a.newelem("div", { class: "class-details" }, [
      a.newelem("span", { class: "class-name" }, [classOption.label]),
      a.newelem("span", { class: "class-schedule-summary" }, [summary]),
    ])

    row.appendChild(details)

    if (className === "All Students") {
      classList.appendChild(row)
      continue
    }

    const controls = createClassScheduleControls(classOption)
    row.appendChild(controls)

    const deleteButton = a.newelem(
      "button",
      { class: "button delete-button", type: "button" },
      ["Delete Class"],
    )
    deleteButton.addEventListener("click", () => removeClass(className))
    controls.appendChild(deleteButton)

    classList.appendChild(row)
  }
}

function formatScheduleSummary(classOption) {
  const days = classOption.days_of_week || "No days selected"
  const start =
    classOption.start_time ? formatTimeForDisplay(classOption.start_time) : "No start time"
  const end =
    classOption.end_time ? formatTimeForDisplay(classOption.end_time) : "No end time"
  if (!classOption.start_time && !classOption.end_time) {
    return `${days}. ${start}. ${end}.`
  }
  return `${days}. ${start} to ${end}.`
}

function formatTimeForDisplay(timeValue) {
  const match = String(timeValue || "").match(/^(\d{1,2}):(\d{2})/)
  if (!match) return timeValue || ""
  let hours = Number(match[1])
  const minutes = match[2]
  const period = hours >= 12 ? "PM" : "AM"
  hours = hours % 12 || 12
  return `${hours}:${minutes} ${period}`
}

function parseStandardTimeInput(value) {
  const rawValue = value.trim()
  if (!rawValue) return { value: "", error: "" }

  const match = rawValue.match(/^(\d{1,2})(?::?(\d{2}))?\s*([ap]m?)?$/i)
  if (!match) {
    return {
      value: "",
      error: "Use a valid time, such as 9:30 AM.",
    }
  }

  let hours = Number(match[1])
  const minutes = Number(match[2] || "00")
  const period = (match[3] || "").toLowerCase()

  if (minutes > 59) {
    return { value: "", error: "Minutes must be between 00 and 59." }
  }
  if (period) {
    if (hours < 1 || hours > 12) {
      return { value: "", error: "Hours must be between 1 and 12." }
    }
    if (period.startsWith("p") && hours !== 12) hours += 12
    if (period.startsWith("a") && hours === 12) hours = 0
  } else if (hours > 23) {
    return {
      value: "",
      error: "Use 1-12 with AM or PM, or 0-23 for 24-hour input.",
    }
  }

  return {
    value: `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`,
    error: "",
  }
}

function validateTimeInput(input) {
  const result = parseStandardTimeInput(input.value)
  const errorNode = input.closest(".schedule-field-label")?.querySelector(".time-input-error")
  input.classList.toggle("invalid-time-input", Boolean(result.error))
  if (errorNode) errorNode.textContent = result.error
  return result
}

function createScheduleTimeInput(className, label, value) {
  const input = a.newelem("input", {
    class: "schedule-time-input",
    type: "text",
    value: value ? formatTimeForDisplay(value) : "",
    placeholder: "9:30 AM",
    inputmode: "text",
    "aria-label": `${className} ${label}`,
  })
  input.addEventListener("input", () => validateTimeInput(input))
  input.addEventListener("blur", () => {
    const result = validateTimeInput(input)
    if (!result.error && result.value) input.value = formatTimeForDisplay(result.value)
  })
  return input
}

function createClassScheduleControls(classOption) {
  const className = classOption.value
  const controls = a.newelem("div", { class: "class-schedule-controls" }, [])
  const startInput = createScheduleTimeInput(className, "Start Time", classOption.start_time)
  const endInput = createScheduleTimeInput(className, "End Time", classOption.end_time)
  const selectedDays = new Set((classOption.days_of_week || "").split(",").filter(Boolean))
  const daysWrap = a.newelem("div", { class: "weekday-picker" }, [])

  for (const weekday of WEEKDAYS) {
    const checkbox = a.newelem("input", {
      type: "checkbox",
      value: weekday,
      checked: selectedDays.has(weekday),
      id: `class-${className}-${weekday}`.replace(/\s+/g, "-"),
    })
    const label = a.newelem("label", { for: checkbox.id }, [weekday.slice(0, 3)])
    daysWrap.append(a.newelem("span", { class: "weekday-option" }, [checkbox, label]))
  }

  const saveButton = a.newelem(
    "button",
    { class: "button", type: "button" },
    ["Save Schedule"],
  )
  saveButton.addEventListener("click", () => saveClassSchedule(className, controls))

  controls.append(
    a.newelem("label", { class: "schedule-field-label" }, [
      "Start Time",
      startInput,
      a.newelem("span", { class: "time-input-error", "aria-live": "polite" }, []),
    ]),
    a.newelem("label", { class: "schedule-field-label" }, [
      "End Time",
      endInput,
      a.newelem("span", { class: "time-input-error", "aria-live": "polite" }, []),
    ]),
    daysWrap,
    saveButton,
  )
  return controls
}

async function saveClassSchedule(className, controls) {
  const checkedDays = Array.from(controls.querySelectorAll(".weekday-picker input:checked"))
    .map((checkbox) => checkbox.value)
    .join(",")
  const timeInputs = controls.querySelectorAll(".schedule-time-input")
  const startTime = validateTimeInput(timeInputs[0])
  const endTime = validateTimeInput(timeInputs[1])
  if (startTime.error || endTime.error) return

  const formData = new FormData()
  formData.append("name", className)
  formData.append("start_time", startTime.value)
  formData.append("end_time", endTime.value)
  formData.append("days_of_week", checkedDays)

  const data = await (
    await fetch("/api/classes/schedule", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to save class schedule.")
    return
  }

  await loadClasses(className)
}

async function addClass() {
  const input = a.qs("#newClassName")
  const className = input.value.trim()
  if (!className) return

  const formData = new FormData()
  formData.append("name", className)

  const data = await (
    await fetch("/api/classes", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to add class.")
    return
  }

  input.value = ""
  await loadClasses(className)
}

async function removeClass(className) {
  const formData = new FormData()
  formData.append("name", className)

  const data = await (
    await fetch("/api/classes/remove", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to delete class.")
    return
  }

  document.querySelectorAll(".student-class").forEach((label) => {
    if (label.textContent === `Class: ${className}`) {
      label.textContent = "Class: All Students"
      label.closest(".roster-student-row")?.setAttribute("data-class-name", "All Students")
    }
  })
  await loadClasses("All Students")
  updateStudentClassSelectors("All Students")
}

a.listen("#addNewClass", "click", addClass)

a.listen("#addNewStudent", "click", async function () {
  const formData = new FormData()
  var firstNameInput = a.qs("#fname")
  var lastNameInput = a.qs("#lname")
  var fname = firstNameInput.value.trim()
  var lname = lastNameInput.value.trim()
  var className = getSelectedClass()
  if (!fname && !lname) return
  if (!className || className === "All Students") {
    setAddStudentStatus("")
    alert("Choose a class code before adding a student.")
    return
  }

  formData.append("fname", fname)
  formData.append("lname", lname)
  formData.append("class_name", className)

  var data = await (
    await fetch("/api/addStudents", {
      method: "POST",
      body: formData,
    })
  ).json()
  if (data.status !== "success") {
    setAddStudentStatus(data.message || "Unable to add student.", true)
    return
  }
  var id = data?.id
  log(fname, lname, id, false, data)
  newNode(fname, lname, id, false, data.class_name)
  firstNameInput.value = ""
  lastNameInput.value = ""
  setAddStudentStatus("Student added.")
})

async function loadRosterStudents() {
  main.innerHTML = ""
  var students = await (await fetch("/api/students")).json()
  for (var s of students) newNode(...s)
  applyRosterClassFilter()
}

async function uploadRosterCsvFile() {
  const selectedClass = getSelectedClass()
  if (!selectedClass || selectedClass === "All Students") {
    setRosterCsvStatus("Choose a class code before uploading a CSV.", true)
    return
  }
  if (!rosterCsvFile.files?.length) {
    setRosterCsvStatus("Choose a CSV file to upload.", true)
    return
  }

  setRosterCsvStatus(`Uploading ${rosterCsvFile.files[0].name}...`)
  const formData = new FormData()
  formData.append("class_name", selectedClass)
  formData.append("csv_file", rosterCsvFile.files[0])

  const data = await (
    await fetch("/api/students/importCsv", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    setRosterCsvStatus(data.message || "Unable to import roster CSV.", true)
    return
  }

  rosterCsvFile.value = ""
  setRosterCsvStatus(
    `Added ${data.count} student${data.count === 1 ? "" : "s"} to ${data.class_name}.`,
  )
  await loadRosterStudents()
}

a.listen("#uploadRosterCsv", "click", uploadRosterCsvFile)
classSelect.addEventListener("change", syncClassAssignmentState)
rosterClassFilter.addEventListener("change", applyRosterClassFilter)

;(async () => {
  await loadClasses()
  await loadRosterStudents()
  a.listen("#toggleShowDisabled", "change", function () {
    a.qs("#main").classList.toggle("showDisabled", this.checked)
  })
})()

async function unregisterStudent(id, container) {
  const formData = new FormData()
  formData.append("studentId", id)

  const data = await (
    await fetch("/api/unregisterStudent", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to unregister student.")
    return
  }

  renderStudentActions(id, container, false)
}

async function deleteStudent(id, container) {
  const formData = new FormData()
  formData.append("studentId", id)
  formData.append("action", "delete")
  formData.append("deleteStudent", "true")

  const data = await (
    await fetch("/api/deleteStudent", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to delete student.")
    return
  }

  container.remove()
}

async function updateStudentClass(id, className, container) {
  const formData = new FormData()
  formData.append("studentId", id)
  formData.append("class_name", className)

  const data = await (
    await fetch("/api/students/updateClass", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to update student class.")
    return
  }

  container.querySelector(".student-class").textContent = `Class: ${data.class_name}`
  container.dataset.className = data.class_name
  applyRosterClassFilter()
}

async function updateStudentName(id, fname, lname, container) {
  const formData = new FormData()
  formData.append("studentId", id)
  formData.append("fname", fname)
  formData.append("lname", lname)

  const data = await (
    await fetch("/api/students/updateName", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to update student name.")
    return false
  }

  container.dataset.fname = data.fname
  container.dataset.lname = data.lname
  if (typeof data.prefName === "string") {
    container.dataset.prefName = data.prefName
  }
  container.dataset.nameEdited = "true"
  container.querySelector(".name").textContent = data.fullName
  return true
}

async function updateStudentPreferredName(id, prefName, container) {
  const formData = new FormData()
  formData.append("studentId", id)
  formData.append("pref_name", prefName)

  const data = await (
    await fetch("/api/students/updatePreferredName", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to update preferred name.")
    return false
  }

  container.dataset.prefName = data.prefName || ""
  container.querySelector(".name").textContent = data.fullName
  return true
}

function isAutomaticNewStudentName(fname, lname) {
  return fname === "New" && /^Student\s+\d+$/.test(lname || "")
}

function createStudentClassSelect(id, selectedClass, container) {
  const select = a.newelem(
    "select",
    { class: "student-class-select", "aria-label": "Student Class" },
    [],
  )
  populateClassSelect(select, selectedClass)
  select.addEventListener("change", () => updateStudentClass(id, select.value, container))
  return select
}

function populateClassSelect(select, selectedClass) {
  select.innerHTML = ""
  for (const classOption of classes) {
    const option = document.createElement("option")
    option.value = classOption.value
    option.textContent = classOption.label
    option.selected = classOption.value === selectedClass
    select.appendChild(option)
  }
}

function updateStudentClassSelectors(fallbackClass = "All Students") {
  document.querySelectorAll(".student-class-select").forEach((select) => {
    const selectedClass =
      classes.some((classOption) => classOption.value === select.value) ?
        select.value
      : fallbackClass
    populateClassSelect(select, selectedClass)
  })
}

function createRegistrationButton(id, container, studentRegistered) {
  const button = a.newelem(
    "button",
    {
      class: `button ${studentRegistered ? "unregister-button" : "register-button"}`,
      type: "button",
    },
    [
      studentRegistered ?
        "Unregister Student"
      : "Register Student",
    ],
  )
  button.addEventListener(
    "click",
    () => {
      if (studentRegistered) {
        unregisterStudent(id, container)
        return
      }
      window.location.href = `/camera?registerId=${id}`
    },
  )
  return button
}

function createEditNameButton(id, container) {
  const button = a.newelem(
    "button",
    { class: "button edit-name-button", type: "button" },
    ["Edit Name"],
  )
  button.addEventListener("click", () => showNameEditor(id, container))
  return button
}

function createPreferredNameButton(id, container) {
  const button = a.newelem(
    "button",
    { class: "button preferred-name-button", type: "button" },
    ["Preferred Name"],
  )
  button.addEventListener("click", () => showPreferredNameEditor(id, container))
  return button
}

function createDeleteButton(id, container) {
  const button = a.newelem(
    "button",
    { class: "button delete-button", type: "button" },
    ["Delete Student"],
  )
  button.addEventListener("click", () => deleteStudent(id, container))
  return button
}

function renderStudentActions(id, container, studentRegistered) {
  const actions = container.querySelector(".actions")
  actions.innerHTML = ""
  actions.appendChild(createEditNameButton(id, container))
  actions.appendChild(createPreferredNameButton(id, container))
  actions.appendChild(createRegistrationButton(id, container, studentRegistered))
  actions.appendChild(createDeleteButton(id, container))
}

function showNameEditor(id, container) {
  const editor = container.querySelector(".student-name-editor")
  editor.innerHTML = ""
  const shouldPrefillName = container.dataset.nameEdited === "true"

  const firstNameInput = a.newelem("input", {
    class: "student-name-input",
    type: "text",
    value: shouldPrefillName ? container.dataset.fname || "" : "",
    placeholder: "First Name",
  })
  const lastNameInput = a.newelem("input", {
    class: "student-name-input",
    type: "text",
    value: shouldPrefillName ? container.dataset.lname || "" : "",
    placeholder: "Last Name",
  })
  const saveButton = a.newelem(
    "button",
    { class: "button", type: "button" },
    ["Save Name"],
  )
  const cancelButton = a.newelem(
    "button",
    { class: "button", type: "button" },
    ["Cancel"],
  )

  saveButton.addEventListener("click", async () => {
    const fname = firstNameInput.value.trim()
    const lname = lastNameInput.value.trim()
    if (!fname && !lname) {
      alert("Student name cannot be empty.")
      return
    }

    const updated = await updateStudentName(id, fname, lname, container)
    if (updated) editor.innerHTML = ""
  })
  cancelButton.addEventListener("click", () => {
    editor.innerHTML = ""
  })

  editor.append(firstNameInput, lastNameInput, saveButton, cancelButton)
  firstNameInput.focus()
}

function showPreferredNameEditor(id, container) {
  const editor = container.querySelector(".student-name-editor")
  editor.innerHTML = ""

  const preferredNameInput = a.newelem("input", {
    class: "student-name-input",
    type: "text",
    value: container.dataset.prefName || "",
    placeholder: "Preferred Name",
  })
  const saveButton = a.newelem(
    "button",
    { class: "button", type: "button" },
    ["Save Preferred Name"],
  )
  const clearButton = a.newelem(
    "button",
    { class: "button", type: "button" },
    ["Clear"],
  )
  const cancelButton = a.newelem(
    "button",
    { class: "button", type: "button" },
    ["Cancel"],
  )

  saveButton.addEventListener("click", async () => {
    const updated = await updateStudentPreferredName(id, preferredNameInput.value.trim(), container)
    if (updated) editor.innerHTML = ""
  })
  clearButton.addEventListener("click", async () => {
    const updated = await updateStudentPreferredName(id, "", container)
    if (updated) editor.innerHTML = ""
  })
  cancelButton.addEventListener("click", () => {
    editor.innerHTML = ""
  })

  editor.append(preferredNameInput, saveButton, clearButton, cancelButton)
  preferredNameInput.focus()
}

function newNode(
  fname,
  lname,
  id,
  studentRegistered,
  className = "All Students",
  prefName = "",
  displayName = "",
) {
  const resolvedDisplayName = displayName || [fname, lname].filter(Boolean).join(" ")
  const container = a.newelem(
    "div",
    {
      class: "container roster-student-row",
      "data-fname": fname,
      "data-lname": lname,
      "data-pref-name": prefName || "",
      "data-class-name": className,
      "data-name-edited": isAutomaticNewStudentName(fname, lname) ? "false" : "true",
    },
    [
      a.newelem("span", { class: "name" }, [resolvedDisplayName]),
      a.newelem("div", { class: "student-name-editor" }, []),
      a.newelem("span", { class: "student-class" }, [`Class: ${className}`]),
      a.newelem("div", { class: "student-class-control" }, []),
      a.newelem("div", { class: "actions" }, []),
    ],
  )

  container
    .querySelector(".student-class-control")
    .append(
      a.newelem("span", { class: "class-change-label" }, ["CHANGE CLASS"]),
      createStudentClassSelect(id, className, container),
    )

  const actions = container.querySelector(".actions")
  renderStudentActions(id, container, studentRegistered)

  main.appendChild(container)
}
