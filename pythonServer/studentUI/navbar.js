const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "Dashboard", href: "/teacher" },
  { label: "Attendance", href: "/attendance" },
  { label: "Roster", href: "/roster" },
  { label: "Camera", href: "/camera" },
]

function initNav() {
  renderLinks()
}

function renderLinks() {
  const nav = document.getElementById("nav-links")
  if (!nav) return

  const currentPath = window.location.pathname

  nav.innerHTML = NAV_LINKS.map(({ label, href }) => {
    const normalizedHref = href === "/" ? "/" : href.replace(/\/$/, "")
    const normalizedPath = currentPath.replace(/\/$/, "") || "/"
    const isActive = normalizedPath === normalizedHref

    return `<span class="nav-link-wrap">
      <a href="${href}" class="${isActive ? "active" : ""}">${label}</a>
    </span>`
  }).join("")
}

if (
  localStorage.alwaysShowNav == "1" ||
  !["/camera", ""].includes(location.pathname.replace(/\/$/, ""))
)
  document.addEventListener("DOMContentLoaded", initNav)
