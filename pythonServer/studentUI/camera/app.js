var registerName = null
Object.assign(window, console)

const ALL_STUDENTS = "__all__"
const CLASS_STORAGE_KEY = "cameraSelectedClass"
const CIRCLE_SEGMENTS = 12

let currentClass = ALL_STUDENTS
let lastFaces = []
let isRecognized = false
let recognizedStudentName = ""
let segmentsFilled = new Set()
let segmentBlobs = {}
let registerState = null
let registerStartTimer = null
let registerFaces = []
let registerId = null
let lastPixels = null
let tempFaceUploadInFlight = false
let isSending = false

const attendanceWritesInFlight = new Set()
const autoMarked = new Set()

const video = document.getElementById("cameraVideo")
const captureCanvas = new OffscreenCanvas(400, 300)
const overlayCanvas = document.getElementById("overlayCanvas")
const faceIdCanvas = document.getElementById("faceIdCircle")
const faceIdWrap = document.getElementById("faceIdWrap")
const classSelect = document.getElementById("cameraClassSelect")
const headerEl = document.getElementById("recognitionHeader")
const cameraMessageEl = document.getElementById("cameraMessage")

const captureCtx = captureCanvas.getContext("2d", {
  willReadFrequently: true,
})
const overlayCtx = overlayCanvas.getContext("2d")
const faceIdCtx = faceIdCanvas.getContext("2d")

async function startCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: true,
  })
  video.srcObject = stream
  cameraMessageEl.textContent = "Camera active. Looking for a face..."
  sendFrame()
}

function setCameraMessage(message) {
  if (cameraMessageEl) cameraMessageEl.textContent = message
}

function showRecognitionFailure(message) {
  const fallback =
    message || "Face recognition is temporarily unavailable."
  headerEl.textContent = fallback
  setCameraMessage(fallback)
  lastFaces = []
}

function getCurrentClassLabel() {
  return classSelect?.selectedOptions?.[0]?.textContent || "All Students"
}

function getKnownFaces() {
  return lastFaces.filter((face) => face.name !== "Unknown" && face.name !== "__TEMP__")
}

function formatClassList(classNames) {
  const uniqueClasses = [...new Set(classNames.filter(Boolean))]
  if (!uniqueClasses.length) return getCurrentClassLabel()
  if (uniqueClasses.length === 1) return uniqueClasses[0]
  if (uniqueClasses.length === 2) return `${uniqueClasses[0]} and ${uniqueClasses[1]}`
  return `${uniqueClasses.slice(0, -1).join(", ")}, and ${uniqueClasses.at(-1)}`
}

function formatList(items) {
  if (items.length <= 1) return items[0] || ""
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(", ")}, and ${items.at(-1)}`
}

function getRecognizedFaceMessage() {
  const knownFaces = getKnownFaces()
  const count = knownFaces.length
  const studentWord = count === 1 ? "student" : "students"
  const recognizedPeople = formatList(
    knownFaces.map((face) => `${face.name} from ${face.class_name || "All Students"}`),
  )
  return `Recognized ${count} ${studentWord}: ${recognizedPeople}.`
}

function getDetectedFaceMessage() {
  if (!lastFaces.length) return "No faces detected."

  const knownFaces = getKnownFaces()
  if (knownFaces.length) return getRecognizedFaceMessage()

  const faceWord = lastFaces.length === 1 ? "face" : "faces"
  return `${lastFaces.length} ${faceWord} detected.`
}

function updateDetectedFaceMessages() {
  const message = getDetectedFaceMessage()
  headerEl.textContent = message
  setCameraMessage(message)
}

function updateRecognitionHeader() {
  if (registerState === "timer" || registerState === "collecting") return

  if (isRecognized) {
    headerEl.textContent = "Welcome, " + recognizedStudentName + "!"
  } else {
    headerEl.textContent =
      `Recognizing students from ${getCurrentClassLabel()}.`
  }
  setCameraMessage(headerEl.textContent)
}

function setCurrentClass(value) {
  currentClass = value || ALL_STUDENTS
  localStorage.setItem(CLASS_STORAGE_KEY, currentClass)
  autoMarked.clear()
  lastFaces = []
  isRecognized = false
  recognizedStudentName = ""
  updateRecognitionHeader()
}

async function loadClassOptions() {
  if (!classSelect) return

  classSelect.innerHTML = ""
  try {
    const response = await fetch("/api/classes")
    const data = await response.json()
    const options = data.classes || []
    for (const option of options) {
      const node = document.createElement("option")
      node.value = option.value
      node.textContent = option.label
      classSelect.appendChild(node)
    }
  } catch (error) {
    console.error("Unable to load classes:", error)
    const fallback = document.createElement("option")
    fallback.value = ALL_STUDENTS
    fallback.textContent = "All Students"
    classSelect.appendChild(fallback)
  }

  const urlClass = new URL(location.href).searchParams.get("className")
  const savedClass = localStorage.getItem(CLASS_STORAGE_KEY)
  const preferredClass = urlClass || savedClass || ALL_STUDENTS
  const matchingOption =
    Array.from(classSelect.options).find((option) => option.value === preferredClass)
      ?.value || ALL_STUDENTS

  classSelect.value = matchingOption
  setCurrentClass(matchingOption)
  classSelect.addEventListener("change", (event) => {
    setCurrentClass(event.target.value)
    setCameraMessage(`Recognizing students from ${getCurrentClassLabel()}.`)
  })
}

function drawOverlay() {
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height)
  const width = overlayCanvas.width

  for (const face of lastFaces) {
    const [rawX1, y1, rawX2, y2] = face.box
    const x1 = width - rawX2
    const x2 = width - rawX1
    const centerX = x1 + (x2 - x1) / 2
    const centerY = y1 + (y2 - y1) / 2
    const known = face.name !== "Unknown"
    const color = known ? "#00ff00" : "#ff0000"

    overlayCtx.strokeStyle = color
    overlayCtx.lineWidth = 2
    overlayCtx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    const dirX = (face.direction_x - 0.5) * 2
    const dirY = (face.direction_y - 0.5) * 2
    if (face.name === "__TEMP__") {
      const arrowLength = 50
      const targetX = centerX + dirX * arrowLength
      const targetY = centerY + dirY * arrowLength
      drawArrow(overlayCtx, centerX, centerY, targetX, targetY, color)
    }

    overlayCtx.fillStyle = color
    overlayCtx.font = "20px Arial"
    overlayCtx.strokeStyle = "black"
    overlayCtx.lineWidth = 5
    overlayCtx.lineJoin = "round"

    const text = face.name === "__TEMP__" ? registerName : face.name
    const textX = x1
    const textY = Math.max(y1 - 6, 12)
    overlayCtx.strokeText(text, textX, textY)
    overlayCtx.fillText(text, textX, textY)
  }

  requestAnimationFrame(drawOverlay)
}

function drawArrow(ctx, fromX, fromY, toX, toY, color) {
  const headLength = 10
  const angle = Math.atan2(toY - fromY, toX - fromX)

  ctx.beginPath()
  ctx.strokeStyle = color
  ctx.lineWidth = 3
  ctx.moveTo(fromX, fromY)
  ctx.lineTo(toX, toY)
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(toX, toY)
  ctx.lineTo(
    toX - headLength * Math.cos(angle - Math.PI / 6),
    toY - headLength * Math.sin(angle - Math.PI / 6),
  )
  ctx.moveTo(toX, toY)
  ctx.lineTo(
    toX - headLength * Math.cos(angle + Math.PI / 6),
    toY - headLength * Math.sin(angle + Math.PI / 6),
  )
  ctx.stroke()
}
requestAnimationFrame(drawOverlay)

function hasFrameChanged(ctx, width, height, threshold = 10) {
  const pixels = ctx.getImageData(0, 0, width, height).data
  if (!lastPixels) {
    lastPixels = pixels
    return true
  }

  let diff = 0
  for (let index = 0; index < pixels.length; index += 40) {
    const rDiff = Math.abs(pixels[index] - lastPixels[index])
    const gDiff = Math.abs(pixels[index + 1] - lastPixels[index + 1])
    const bDiff = Math.abs(pixels[index + 2] - lastPixels[index + 2])
    if (rDiff + gDiff + bDiff > 30) diff++
  }

  if (diff > threshold) lastPixels = pixels
  return diff > threshold
}

function directionToSegment(dx, dy) {
  const x = 0.5 - dx
  const y = 0.5 - dy
  const angle = Math.atan2(y, x)
  const degrees = 180 + (((angle * 180) / Math.PI + 360 + 90) % 360)
  return Math.floor(degrees / (360 / CIRCLE_SEGMENTS)) % CIRCLE_SEGMENTS
}

function startRegister() {
  fetch("/delTempFace", {
    method: "POST",
  }).then(() => {
    registerStartTimer = Date.now()
    registerState = "timer"
    registerFaces = []
    resetFaceIdCircle()
    headerEl.textContent = "Move your face in a full circle"
  })
}

async function saveAttendance(name) {
  if (autoMarked.has(name) || attendanceWritesInFlight.has(name)) return true

  attendanceWritesInFlight.add(name)
  try {
    const formData = new FormData()
    formData.append("studentName", name)
    const response = await fetch("/api/attendance/markPresent", {
      method: "POST",
      body: formData,
    })
    const data = await response.json()
    if (!response.ok || data.status !== "success") {
      throw new Error(data.message || "Unable to mark attendance")
    }
    autoMarked.add(name)
    return true
  } catch (error) {
    console.error("Attendance save failed:", error)
    headerEl.textContent = `Could not mark ${name} present.`
    setCameraMessage(`Could not mark ${name} present.`)
    return false
  } finally {
    attendanceWritesInFlight.delete(name)
  }
}

async function autoMarkPresent(name) {
  if (autoMarked.has(name) || attendanceWritesInFlight.has(name)) return

  const saved = await saveAttendance(name)
  if (!saved) return

  isRecognized = true
  recognizedStudentName = name
  updateDetectedFaceMessages()
}

const id = new URL(location.href).searchParams.get("registerId")
if (id) {
  registerId = id
  startRegister()
  ;(async () => {
    registerName = (
      await (await fetch(`/api/getUserName?id=${id}`)).json()
    ).fullName
  })()
}

function drawFaceIdCircle() {
  const width = faceIdCanvas.width
  const height = faceIdCanvas.height
  const cx = width / 2
  const cy = height / 2
  const radius = width * 0.42
  const lineWidth = width * 0.075
  const gap = 0.06
  const segmentAngle = (2 * Math.PI) / CIRCLE_SEGMENTS
  const offset = -Math.PI / 2

  faceIdCtx.clearRect(0, 0, width, height)
  for (let index = 0; index < CIRCLE_SEGMENTS; index++) {
    const start = offset + index * segmentAngle + gap / 2
    const end = offset + (index + 1) * segmentAngle - gap / 2
    faceIdCtx.beginPath()
    faceIdCtx.arc(cx, cy, radius, start, end)

    if (segmentsFilled.has(index)) {
      faceIdCtx.shadowBlur = 12
      faceIdCtx.shadowColor = "#007AFF"
      faceIdCtx.strokeStyle = "#007AFF"
    } else {
      faceIdCtx.shadowBlur = 0
      faceIdCtx.strokeStyle = "rgba(180,180,180,0.35)"
    }

    faceIdCtx.lineWidth = lineWidth
    faceIdCtx.lineCap = "round"
    faceIdCtx.stroke()
  }
}

function resetFaceIdCircle() {
  segmentsFilled = new Set()
  segmentBlobs = {}
  drawFaceIdCircle()
  faceIdWrap.style.display = "flex"
}

function hideFaceIdCircle() {
  faceIdWrap.style.display = "none"
}

function postFace(id, blob) {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append("id", id === "__TEMP__" ? id : Number(id))
    formData.append("image_file", blob, Math.random() + "a.jpeg")
    fetch("/registerStudent", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data)
        resolve(data)
      })
      .catch((error) => {
        console.error("Upload failed: " + error.message)
        reject(error)
      })
  })
}

function findNextUnfilledSegment(fromSegment) {
  for (let offset = 1; offset <= CIRCLE_SEGMENTS; offset++) {
    const candidate = (fromSegment + offset) % CIRCLE_SEGMENTS
    if (!segmentsFilled.has(candidate)) return candidate
  }
  return null
}

async function sendFrame() {
  if (isSending || video.readyState < 2) {
    return requestAnimationFrame(sendFrame)
  }

  await new Promise((resolve) => setTimeout(resolve, 75))
  isSending = true

  try {
    captureCtx.drawImage(
      video,
      0,
      0,
      captureCanvas.width,
      captureCanvas.height,
    )

    if (
      !hasFrameChanged(
        captureCtx,
        captureCanvas.width,
        captureCanvas.height,
      )
    ) {
      return
    }

    const blob = await captureCanvas.convertToBlob({
      type: "image/jpeg",
      quality: 0.8,
    })

    const formData = new FormData()
    formData.append("image_file", blob, "frame.jpg")
    formData.append("class_name", currentClass)

    const response = await fetch("/api/recognizeFrame", {
      method: "POST",
      body: formData,
    })

    const data = await response.json()
    if (!response.ok) {
      showRecognitionFailure(data.message)
      return
    }

    lastFaces = data.faces || []
    updateDetectedFaceMessages()

    if (registerState === "timer") {
      const timeLeft =
        3 - Math.floor((Date.now() - registerStartTimer) / 1000)
      headerEl.textContent =
        `The registration will start in ${timeLeft} second${timeLeft === 1 ? "" : "s"}`
      setCameraMessage(headerEl.textContent)
      if (timeLeft <= 0) {
        registerState = "collecting"
      }
    }

    if (registerState === "collecting") {
      if (lastFaces.length === 0) {
        headerEl.textContent = "Look at the camera to start"
        setCameraMessage(headerEl.textContent)
      } else if (lastFaces.length > 1) {
        headerEl.textContent = "Only one person in frame when registering"
        setCameraMessage(headerEl.textContent)
      } else {
        const face = lastFaces[0]

        if (face.name === "Unknown" && !tempFaceUploadInFlight) {
          headerEl.textContent = "Face detected. Hold still while we capture your starting angle."
          setCameraMessage(headerEl.textContent)
          tempFaceUploadInFlight = true
          try {
            await postFace("__TEMP__", blob)
          } finally {
            tempFaceUploadInFlight = false
          }
        }

        if (face.name !== "__TEMP__") {
          headerEl.textContent =
            "Face detected. Keep your face centered and wait for the guide to start."
          setCameraMessage(headerEl.textContent)
          return
        }

        const segment = directionToSegment(
          face.direction_x,
          face.direction_y,
        )

        if (!segmentBlobs[segment]) {
          segmentBlobs[segment] = blob
          registerFaces.push(blob)
          segmentsFilled.add(segment)
          drawFaceIdCircle()
        }

        const nextSegment = findNextUnfilledSegment(segment)
        if (nextSegment !== null) {
          headerEl.textContent =
            `${segmentsFilled.size} / ${CIRCLE_SEGMENTS} angles captured`
          setCameraMessage(headerEl.textContent)
        }

        if (segmentsFilled.size >= CIRCLE_SEGMENTS) {
          registerState = null
          hideFaceIdCircle()
          headerEl.textContent = "Circle complete! Saving..."
          setCameraMessage(headerEl.textContent)

          fetch("/delTempFace", { method: "POST" }).then(async () => {
            await Promise.all(registerFaces.map((frame) => postFace(registerId, frame)))
            headerEl.textContent = "You were registered!"
            setCameraMessage(headerEl.textContent)
            registerFaces = []
            location.href = "/roster"
          })
        }
      }
    } else {
      for (const face of lastFaces) {
        if (face.name !== "Unknown" && face.name !== "__TEMP__") {
          await autoMarkPresent(face.name)
        }
      }
      updateDetectedFaceMessages()
    }
  } catch (error) {
    console.error("Recognition error:", error)
  } finally {
    isSending = false
    sendFrame()
  }
}

loadClassOptions()
updateRecognitionHeader()
startCamera()
