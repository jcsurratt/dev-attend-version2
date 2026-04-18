let currentClass = "All Students"
let availableClasses = []
const studentsDiv = document.getElementById("students")
const classSelect = document.getElementById("classSelect")
const classSearchInput = document.getElementById("classSearchInput")
const classSearchResults = document.getElementById("classSearchResults")

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
  const classes = availableClasses.filter((classOption) =>
    classOption.label.toLowerCase().includes(classSearch),
  )
  classSelect.innerHTML = ""

  for (const classOption of classes) {
    const option = document.createElement("option")
    option.value = classOption.value
    option.textContent = classOption.label
    classSelect.appendChild(option)
  }

  if (!classSelect.options.length) {
    renderClassSearchResults(classes, classSearch)
    return
  }

  const matchingClass =
    Array.from(classSelect.options).find(
      (option) => option.value === preferredClass,
    )?.value || classSelect.options[0].value

  classSelect.value = matchingClass
  currentClass = matchingClass
  renderClassSearchResults(classes, classSearch)
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

async function renderStudents() {
  studentsDiv.innerHTML = ""
  const selectedClass = getSelectedClass()
  if (!selectedClass) return
  const encodedClass = encodeURIComponent(selectedClass)
  const students = await (
    await fetch(`/api/classStudents?class_name=${encodedClass}`)
  ).json()

  students.forEach((student) => {
    const div = newElement("div", { class: "student attendance-student" }, [
      newElement("span", { class: "attendance-student-name" }, [student.name]),
      newElement("div", { class: "student-class-control" }, [
        newElement("span", { class: "class-change-label" }, ["Change Class"]),
        createStudentClassSelect(student.id, student.class_name || selectedClass),
      ]),
    ])
    studentsDiv.appendChild(div)
  })
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
    await renderStudents()
    return
  }

  await loadClasses(currentClass)
  await renderStudents()
}

window.addClass = async function () {
  const input = document.getElementById("newClassInput")
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
  await renderStudents()
}

window.removeClass = async function () {
  const className = getSelectedClass()
  if (!className || className === "All Students") return

  const formData = new FormData()
  formData.append("name", className)
  const data = await (
    await fetch("/api/classes/remove", {
      method: "POST",
      body: formData,
    })
  ).json()

  if (data.status !== "success") {
    alert(data.message || "Unable to remove class.")
    return
  }

  await loadClasses("All Students")
  await renderStudents()
}

window.addStudent = async function () {
  const input = document.getElementById("newStudentInput")
  const fullName = input.value.trim()
  if (!fullName) return

  const parts = fullName.split(/\s+/)
  const fname = parts.shift() || ""
  const lname = parts.join(" ")

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

  input.value = ""
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
  await renderStudents()
}

classSelect.addEventListener("change", async function () {
  currentClass = getSelectedClass()
  await renderStudents()
})

;(async () => {
  await loadClasses("All Students")
  await renderStudents()
})()
