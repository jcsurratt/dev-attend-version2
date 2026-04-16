var registerName = null
Object.assign(window, console)
let classes = { "ITP 251-M1": [] }
let currentClass = "ITP 251-M1"
const studentsDiv = document.getElementById("students")

const video = document.getElementById("cameraVideo")
const captureCanvas = new OffscreenCanvas(400, 300)
const overlayCanvas = document.getElementById("overlayCanvas")

const captureCtx = captureCanvas.getContext("2d", {
  willReadFrequently: true,
})
const overlayCtx = overlayCanvas.getContext("2d")

const statusEl = document.getElementById("recognitionStatus")

let lastFaces = []

async function startCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: true,
  })
  video.srcObject = stream
  statusEl.textContent = "Camera active"
  sendFrame()
}

function drawOverlay() {
  overlayCtx.clearRect(
    0,
    0,
    overlayCanvas.width,
    overlayCanvas.height,
  )
  const offsetX = faceIdCanvas.width / 2
  const offsetY = faceIdCanvas.height / 2
  // const vbcr = video.getBoundingClientRect()
  // faceIdWrap.style.left = `${vbcr.left + 200 - offsetX}px`
  // faceIdWrap.style.top = `${vbcr.top + 150 - offsetY}px`
  const W = overlayCanvas.width
  for (const face of lastFaces) {
    const [rx1, y1, rx2, y2] = face.box

    // 1. Flip X for mirrored video
    const x1 = W - rx2
    const x2 = W - rx1
    const centerX = x1 + (x2 - x1) / 2
    const centerY = y1 + (y2 - y1) / 2
    // log(face)
    const known = face.name !== "Unknown"
    const color = known ? "#00ff00" : "#ff0000"

    // 2. Draw the bounding box
    overlayCtx.strokeStyle = color
    overlayCtx.lineWidth = 2
    overlayCtx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    // 3. Draw the Direction Arrow
    // Map 0...1 range to -1...1 for vector direction
    const dirX = (face.direction_x - 0.5) * 2
    const dirY = (face.direction_y - 0.5) * 2
    // log(face)

    if (face.name === "__TEMP__") {
      // Arrow length (adjust 50 to change how long the arrow is)
      const arrowLength = 50
      const targetX = centerX + dirX * arrowLength
      const targetY = centerY + dirY * arrowLength
      drawArrow(overlayCtx, centerX, centerY, targetX, targetY, color)
      // if (registerState === "collecting") {
      //   faceIdWrap.style.display = "flex"
      //   // Offset by half the canvas width/height to center it
      //   const offsetX = faceIdCanvas.width / 2
      //   const offsetY = faceIdCanvas.height / 2
      //   faceIdWrap.style.left = `${vbcr.left + centerX - offsetX}px`
      //   faceIdWrap.style.top = `${vbcr.top + centerY - offsetY}px`
      // }
    }
    // 4. Draw Label Text
    overlayCtx.fillStyle = color
    overlayCtx.font = "20px Arial"
    // 1. Set the stroke styles
    overlayCtx.strokeStyle = "black"
    overlayCtx.lineWidth = 5
    overlayCtx.lineJoin = "round" // Prevents sharp spikes on font corners

    const text = `${face.name == "__TEMP__" ? registerName : face.name}`
    const x = x1
    const y = Math.max(y1 - 6, 12)

    // 2. Draw the border first
    overlayCtx.strokeText(text, x, y)

    // 3. Draw the actual text on top
    overlayCtx.fillText(text, x, y)
  }

  requestAnimationFrame(drawOverlay)
}

// Helper function to draw the arrow shape
function drawArrow(ctx, fromX, fromY, toX, toY, color) {
  const headLength = 10 // length of head in pixels
  const angle = Math.atan2(toY - fromY, toX - fromX)

  ctx.beginPath()
  ctx.strokeStyle = color
  ctx.lineWidth = 3
  ctx.moveTo(fromX, fromY)
  ctx.lineTo(toX, toY)
  ctx.stroke()

  // Draw the arrowhead
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

// Poll the server every ~400 ms by capturing a frame and POSTing it
var lastPixels = null
function hasFrameChanged(ctx, width, height, threshold = 10) {
  const pixels = ctx.getImageData(0, 0, width, height).data
  if (!lastPixels) {
    lastPixels = pixels
    return true
  }

  let diff = 0
  // Sample every 10th pixel to keep it fast
  for (let i = 0; i < pixels.length; i += 40) {
    const rDiff = Math.abs(pixels[i] - lastPixels[i])
    const gDiff = Math.abs(pixels[i + 1] - lastPixels[i + 1])
    const bDiff = Math.abs(pixels[i + 2] - lastPixels[i + 2])
    if (rDiff + gDiff + bDiff > 30) diff++
  }

  if (diff > threshold) lastPixels = pixels
  // Return true if more than 'threshold' samples changed
  return diff > threshold
}

// =====================
// FACE-ID CIRCLE (registration UI)
// =====================
const CIRCLE_SEGMENTS = 12 // ring divided into N arc segments
const faceIdCanvas = document.getElementById("faceIdCircle")
const faceIdCtx = faceIdCanvas.getContext("2d")
const faceIdWrap = document.getElementById("faceIdWrap")

let segmentsFilled = new Set() // which arc segments have been covered
let segmentBlobs = {} // segment index -> first blob captured there

/** Convert (direction_x, direction_y) → segment index 0..CIRCLE_SEGMENTS-1.
 *  direction_x: 0=full-left, 0.5=center, 1=full-right
 *  direction_y: 0=full-up,   0.5=center, 1=full-down
 *  We use atan2 so movement maps naturally onto a clock face. */
function directionToSegment(dx, dy) {
  // 1. Map X: If Left is 1 and Right is 0, then (0.5 - dx)
  // makes Right positive (+0.5) and Left negative (-0.5).
  const x = 0.5 - dx

  // 2. Map Y: If Up is 0 and Down is 1, then (0.5 - dy)
  // makes Up positive (+0.5) and Down negative (-0.5).
  const y = 0.5 - dy

  const angle = Math.atan2(y, x) // Returns radians (-π to π)

  // 3. Convert to degrees and normalize to 0-360
  // We add 90 to the degree because the drawing offset is -π/2 (Top)
  const deg = 180 + (((angle * 180) / Math.PI + 360 + 90) % 360)

  // 4. Calculate segment
  return Math.floor(deg / (360 / CIRCLE_SEGMENTS)) % CIRCLE_SEGMENTS
}
let isRecognized = false
let recognizedStudentName = ""
function startRegister() {
  fetch("/delTempFace", {
    method: "POST",
  }).then(() => {
    registerStartTimer = Date.now()
    registerState = "timer"
    registerFaces = []
    resetFaceIdCircle()
    document.getElementById("recognitionHeader").textContent =
      "Move your face in a full circle"
  })
}
const autoMarked = new Set() // prevent duplicate auto-marking

function autoMarkPresent(name) {
  if (autoMarked.has(name)) return

  // Add to class roster if not already there
  if (!classes[currentClass].includes(name)) {
    classes[currentClass].push(name)
    renderStudents()
  }

  // Find and mark the student row
  const divs = document.querySelectorAll(".student")
  divs.forEach((div) => {
    if (div.dataset.name === name) {
      markStatus(div, "present")
      autoMarked.add(name)

      isRecognized = true
      recognizedStudentName = name
      updateRecognitionHeader()
    }
  })
}
function renderStudents() {
  studentsDiv.innerHTML = ""
  classes[currentClass].forEach((name) => addStudentToList(name))
}

function addStudent() {
  const input = document.getElementById("newStudentInput")
  const name = input.value.trim()
  if (!name) return
  if (!classes[currentClass].includes(name))
    classes[currentClass].push(name)
  renderStudents()
  input.value = ""
}

function addStudentToList(name) {
  const div = document.createElement("div")
  div.className = "student"
  div.dataset.name = name // used by autoMarkPresent()
  div.innerHTML = `
      ${name}
      <button onclick="markStatus(this.parentElement,'present')">Present</button>
      <button onclick="markStatus(this.parentElement,'tardy')">Tardy</button>
      <button onclick="markStatus(this.parentElement,'absent')">Absent</button>
      <span class="timestamp"></span>
    `
  studentsDiv.appendChild(div)
}

// =====================
// MARK STATUS
// =====================
function markStatus(studentDiv, status) {
  studentDiv.classList.remove("present", "tardy", "absent")
  studentDiv.classList.add(status)
  const ts = studentDiv.querySelector(".timestamp")
  const now = new Date().toLocaleString()
  ts.textContent = ` (${
    status.charAt(0).toUpperCase() + status.slice(1)
  } at ${now})`
}

// =====================
// SEARCH
// =====================
function searchStudents() {
  const filter = document
    .getElementById("searchInput")
    .value.toLowerCase()
  const divs = document.querySelectorAll(".student")
  divs.forEach((div) => {
    div.style.display =
      div.dataset.name.toLowerCase().includes(filter) ? "" : "none"
  })
}

function updateRecognitionHeader() {
  const header = document.getElementById("recognitionHeader")
  if (isRecognized) {
    header.textContent = "Welcome, " + recognizedStudentName + "!"
  } else {
    header.textContent = "Student currently not recognised."
  }
}

var registerId = null
var id = new URL(location.href).searchParams.get("registerId")
if (id) {
  registerId = id
  startRegister()
  ;(async () => {
    registerName = (
      await (await fetch(`/api/getUserName?id=${id}`)).json()
    ).fullName
  })()
}
/** Render the ring.  Filled segments glow blue; empty ones are dim white. */
function drawFaceIdCircle() {
  const W = faceIdCanvas.width
  const H = faceIdCanvas.height
  const cx = W / 2
  const cy = H / 2
  const r = W * 0.42
  const lw = W * 0.075
  const gap = 0.06 // radians of gap between segments

  faceIdCtx.clearRect(0, 0, W, H)

  const segAngle = (2 * Math.PI) / CIRCLE_SEGMENTS
  // start at the top of the clock (-π/2)
  const offset = -Math.PI / 2

  for (let i = 0; i < CIRCLE_SEGMENTS; i++) {
    const start = offset + i * segAngle + gap / 2
    const end = offset + (i + 1) * segAngle - gap / 2

    faceIdCtx.beginPath()
    faceIdCtx.arc(cx, cy, r, start, end)

    if (segmentsFilled.has(i)) {
      // Glowing blue segment
      faceIdCtx.shadowBlur = 12
      faceIdCtx.shadowColor = "#007AFF"
      faceIdCtx.strokeStyle = "#007AFF"
    } else {
      faceIdCtx.shadowBlur = 0
      faceIdCtx.strokeStyle = "rgba(180,180,180,0.35)"
    }
    faceIdCtx.lineWidth = lw
    faceIdCtx.lineCap = "round"
    faceIdCtx.stroke()
  }

  // Centre text: how many done
  // faceIdCtx.shadowBlur = 0
  // faceIdCtx.fillStyle = "#333"
  // faceIdCtx.font = `bold ${W * 0.14}px Arial`
  // faceIdCtx.textAlign = "center"
  // faceIdCtx.textBaseline = "middle"
  // const pct = Math.round(
  //   (segmentsFilled.size / CIRCLE_SEGMENTS) * 100,
  // )
  // faceIdCtx.fillText(pct + "%", cx, cy)
}

/** Call when registration starts - reset the ring. */
function resetFaceIdCircle() {
  segmentsFilled = new Set()
  segmentBlobs = {}
  drawFaceIdCircle()
  faceIdWrap.style.display = "flex"
}

/** Call when registration finishes - hide the ring. */
function hideFaceIdCircle() {
  faceIdWrap.style.display = "none"
}

// =====================
// REGISTRATION STATE
// =====================
// registerState:
//   null            → not registering
//   "collecting"    → sweeping face around circle
var registerState = null
var registerStartTimer = null
var registerFaces = []

function postFace(id, blob) {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append("id", id == "__TEMP__" ? id : Number(id))
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
      .catch((err) => {
        console.error("Upload failed: " + err.message)
        reject(err)
      })
  })
}
var tempFaceUploadInFlight = false
var isSending = false
async function sendFrame() {
  if (isSending || video.readyState < 2)
    return requestAnimationFrame(sendFrame)
  await new Promise((e) => setTimeout(e, 100))
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
      return // Skip sending
    }
    const blob = await captureCanvas.convertToBlob({
      type: "image/jpeg",
      quality: 0.8,
    })

    const formData = new FormData()
    formData.append("image_file", blob, "frame.jpg")

    const response = await fetch("/api/recognizeFrame", {
      method: "POST",
      body: formData,
    })

    if (response.ok) {
      const data = await response.json()
      lastFaces = data.faces || []
      statusEl.textContent =
        lastFaces.length ?
          `${lastFaces.length} face(s) detected`
        : "No faces detected"

      if (registerState === "timer") {
        var timeLeft =
          3 - Math.floor((Date.now() - registerStartTimer) / 1000)
        document.getElementById("recognitionHeader").textContent =
          `The registration will start in ${timeLeft} second${timeLeft == 1 ? "" : "s"}`
        if (timeLeft <= 0) {
          registerState = "collecting"
        }
      }
      if (registerState === "collecting") {
        // ── Registration: fill circle segments ──
        if (lastFaces.length === 0) {
          document.getElementById("recognitionHeader").textContent =
            "Look at the camera to start"
          // faceIdHint.textContent = "Move your head in a circle"
        } else if (lastFaces.length > 1) {
          document.getElementById("recognitionHeader").textContent =
            "Only one person in frame when registering"
        } else {
          const face = lastFaces[0]

          // Always capture temp embeddings for every frame so the server
          // builds a multi-angle embedding set under __TEMP__
          if (face.name === "Unknown" && !tempFaceUploadInFlight) {
            tempFaceUploadInFlight = true
            try {
              await postFace("__TEMP__", blob)
            } finally {
              tempFaceUploadInFlight = false
            }
          }

          if (face.name !== "__TEMP__") {
            return
          }

          // Map current head direction to a circle segment
          const seg = directionToSegment(
            face.direction_x,
            face.direction_y,
          )

          if (!segmentBlobs[seg]) {
            // First time we hit this segment - save the blob
            segmentBlobs[seg] = blob
            registerFaces.push(blob)
            segmentsFilled.add(seg)
            drawFaceIdCircle()
          }

          // Prompt hint: nudge user toward next unfilled segment
          const nextSeg = findNextUnfilledSegment(seg)
          if (nextSeg !== null) {
            // const hint = segmentToHint(nextSeg)
            // faceIdHint.textContent = hint
            document.getElementById("recognitionHeader").textContent =
              `${segmentsFilled.size} / ${CIRCLE_SEGMENTS} angles captured`
          }

          // ── All segments filled → finish registration ──
          if (segmentsFilled.size >= CIRCLE_SEGMENTS) {
            registerState = null
            hideFaceIdCircle()
            document.getElementById("recognitionHeader").textContent =
              "Circle complete! Saving…"

            fetch("/delTempFace", { method: "POST" }).then(
              async () => {
                await Promise.all(
                  registerFaces.map((f) => postFace(registerId, f)),
                )
                document.getElementById(
                  "recognitionHeader",
                ).textContent = `you were registered!`
                registerState = null
                registerFaces = []
                location.href = "/roster"
              },
            )
          }
        }
      } else {
        // Normal attendance mode: auto-mark recognised students
        for (const face of lastFaces) {
          if (face.name !== "Unknown") {
            autoMarkPresent(face.name)
          }
        }
      }
    }
  } catch (err) {
    console.error("Recognition error:", err)
  } finally {
    isSending = false
    sendFrame()
  }
}

/** Find the next unfilled segment (clockwise from current). */
function findNextUnfilledSegment(fromSeg) {
  for (let offset = 1; offset <= CIRCLE_SEGMENTS; offset++) {
    const candidate = (fromSeg + offset) % CIRCLE_SEGMENTS
    if (!segmentsFilled.has(candidate)) return candidate
  }
  return null // all filled
}
startCamera()
