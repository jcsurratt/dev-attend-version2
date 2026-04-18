Object.assign(globalThis, console)
const a = loadlib("allfuncs")

var main = a.qs("#main")
var classSelect = a.qs("#class_name")
var classList = a.qs("#classList")
var classes = []

function getSelectedClass() {
  return classSelect.value || "All Students"
}

async function loadClasses(preferredClass = null) {
  const data = await (await fetch("/api/classes")).json()
  classes = data.classes || []

  classSelect.innerHTML = ""
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
      )?.value || classSelect.options[0].value
    classSelect.value = selected
  }

  renderClassList()
  updateStudentClassSelectors(preferredClass || "All Students")
}

function renderClassList() {
  classList.innerHTML = ""
  if (!classes.length) {
    classList.appendChild(a.newelem("p", { class: "empty-state" }, ["No classes yet."]))
    return
  }

  for (const classOption of classes) {
    const className = classOption.value
    const row = a.newelem("div", { class: "class-row" }, [
      a.newelem("span", { class: "class-name" }, [classOption.label]),
    ])

    if (className !== "All Students") {
      const deleteButton = a.newelem(
        "button",
        { class: "button delete-button", type: "button" },
        ["Delete Class"],
      )
      deleteButton.addEventListener("click", () => removeClass(className))
      row.appendChild(deleteButton)
    }

    classList.appendChild(row)
  }
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
    }
  })
  await loadClasses("All Students")
  updateStudentClassSelectors("All Students")
}

a.listen("#addNewClass", "click", addClass)

a.listen("#addNewStudent", "click", async function () {
  const formData = new FormData()
  var fname = a.qs("#fname").value.trim()
  var lname = a.qs("#lname").value.trim()
  var className = getSelectedClass()
  if (!fname && !lname) return

  formData.append("fname", fname)
  formData.append("lname", lname)
  formData.append("class_name", className)

  var data = await (
    await fetch("/api/addStudents", {
      method: "POST",
      body: formData,
    })
  ).json()
  var id = data?.id
  log(fname, lname, id, false, data)
  newNode(fname, lname, id, false, data.class_name)
})
;(async () => {
  await loadClasses("All Students")
  var students = await (await fetch("/api/students")).json()
  a.listen("#toggleShowDisabled", "change", function () {
    a.qs("#main").classList.toggle("showDisabled", this.checked)
  })
  for (var s of students) newNode(...s)
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

  const actions = container.querySelector(".actions")
  actions.innerHTML = ""
  actions.appendChild(createEditNameButton(id, container))
  actions.appendChild(createRegisterLink(id, false))
  actions.appendChild(createDeleteButton(id, container))
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
  container.dataset.nameEdited = "true"
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

function createRegisterLink(id, studentRegistered) {
  const button = a.newelem(
    "button",
    { disabled: studentRegistered, class: "button" },
    [
      studentRegistered ?
        "Student Registered"
      : "Register Student",
    ],
  )

  return a.newelem(
    "a",
    { href: `/camera?registerId=${id}`, class: "link" },
    [button],
  )
}

function createUnregisterButton(id, container) {
  const button = a.newelem(
    "button",
    { class: "button unregister-button", type: "button" },
    ["Unregister Student"],
  )
  button.addEventListener("click", () => unregisterStudent(id, container))
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

function createDeleteButton(id, container) {
  const button = a.newelem(
    "button",
    { class: "button delete-button", type: "button" },
    ["Delete Student"],
  )
  button.addEventListener("click", () => deleteStudent(id, container))
  return button
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

function newNode(fname, lname, id, studentRegistered, className = "All Students") {
  const container = a.newelem(
    "div",
    {
      class: "container",
      "data-fname": fname,
      "data-lname": lname,
      "data-name-edited": isAutomaticNewStudentName(fname, lname) ? "false" : "true",
    },
    [
      a.newelem("span", { class: "name" }, [fname, " ", lname]),
      a.newelem("div", { class: "student-name-editor" }, []),
      a.newelem("span", { class: "student-class" }, [`Class: ${className}`]),
      a.newelem("div", { class: "student-class-control" }, []),
      a.newelem("div", { class: "actions" }, []),
    ],
  )

  container
    .querySelector(".student-class-control")
    .append(
      a.newelem("span", { class: "class-change-label" }, ["Change Class"]),
      createStudentClassSelect(id, className, container),
    )

  const actions = container.querySelector(".actions")
  actions.appendChild(createEditNameButton(id, container))
  actions.appendChild(createRegisterLink(id, studentRegistered))
  if (studentRegistered) {
    actions.appendChild(createUnregisterButton(id, container))
  }
  actions.appendChild(createDeleteButton(id, container))

  main.appendChild(container)
}
