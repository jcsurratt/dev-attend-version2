Object.assign(globalThis, console)
const a = loadlib("allfuncs")

var main = a.qs("#main")
a.listen("#addNewStudent", "click", async function () {
  const formData = new FormData()
  var fname = a.qs("#fname").value
  var lname = a.qs("#lname").value
  formData.append("fname", fname)
  formData.append("lname", lname)

  var data = await (
    await fetch("/api/addStudents", {
      method: "POST",
      body: formData,
    })
  ).json()
  var id = data?.id
  log(fname, lname, id, false, data)
  newNode(fname, lname, id, false)
})
;(async () => {
  var students = await (await fetch("/api/students")).json()
  a.listen("#toggleShowDisabled", "change", function () {
    a.qs("#main").classList.toggle("showDisabled", this.checked)
  })
  for (var s of students) newNode(...s)
})()

function newNode(fname, lname, id, studentRegistered) {
  main.appendChild(
    a.newelem(
      "div",
      {
        class: "container",
      },
      [
        a.newelem("span", { class: "name" }, [fname, " ", lname]),
        a.newelem(
          "a",
          { href: `/camera?registerId=${id}`, class: "link" },
          [
            a.newelem(
              "button",
              { disabled: studentRegistered, class: "button" },
              [
                studentRegistered ?
                  "student registered"
                : "register student",
              ],
            ),
          ],
        ),
      ],
    ),
  )
}
