let classes = { "ITP 251-M1": [] }
let currentClass = "ITP 251-M1"
const studentsDiv = document.getElementById("students")
const classSelect = document.getElementById("classSelect")

function updateDropdown() {
  classSelect.innerHTML = ""
  for (let c in classes) {
    const option = document.createElement("option")
    option.value = c
    option.textContent = c
    classSelect.appendChild(option)
  }
}

function renderStudents() {
  studentsDiv.innerHTML = ""
  classes[currentClass].forEach((name) => {
    const div = document.createElement("div")
    div.className = "student"
    div.textContent = name
    studentsDiv.appendChild(div)
  })
}

window.addClass = function () {
  const input = document.getElementById("newClassInput")
  classes[input.value] = []
  updateDropdown()
}

window.removeClass = function () {
  delete classes[currentClass]
  updateDropdown()
}

window.addStudent = function () {
  const input = document.getElementById("newStudentInput")
  classes[currentClass].push(input.value)
  renderStudents()
}

window.searchStudents = function () {
  const filter = document
    .getElementById("searchInput")
    .value.toLowerCase()
  document.querySelectorAll(".student").forEach((div) => {
    div.style.display =
      div.textContent.toLowerCase().includes(filter) ? "" : "none"
  })
}

updateDropdown()
renderStudents()
