const galleryInput = document.getElementById("galleryInput");
const cameraInput = document.getElementById("cameraInput");
const preview = document.getElementById("preview");
const cameraPreview = document.getElementById("cameraPreview");
const cameraCanvas = document.getElementById("cameraCanvas");
const cameraActions = document.getElementById("cameraActions");
const cameraHelp = document.getElementById("cameraHelp");
const placeholder = document.getElementById("placeholder");
const analyzeBtn = document.getElementById("analyzeBtn");
const analysisMessage = document.getElementById("analysisMessage");
const resetBtn = document.getElementById("resetBtn");
const fileName = document.getElementById("fileName");
const result = document.getElementById("result");
const dropzone = document.getElementById("dropzone");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");

let selectedFile = null;
let previewUrl = null;
let cameraStream = null;
let scanCount = 0;
let healthyCount = 0;
let diseaseCount = 0;
const recentScans = [];
let currentUser = null;
let csrfToken = null;
let authMode = "login";
let lastPrediction = null;

const placeholders = {
  reports: ["Reports", "Printable diagnosis reports will be available in Phase 6", "▤"],
  settings: ["Settings", "Account and language preferences will be available in later phases", "⚙"]
};

Object.entries(placeholders).forEach(([name, [title, description, icon]]) => {
  const view = document.getElementById(`view-${name}`);
  view.innerHTML = `
    <div class="feature-placeholder">
      <div>
        <div class="empty-icon">${icon}</div>
        <h1>${title}</h1>
        <p>${description}</p>
        <button class="secondary-button" type="button" data-view="scanner">Open AI Scanner</button>
      </div>
    </div>`;
});

const gardenView = document.getElementById("view-garden");
gardenView.innerHTML = `
  <div class="page-heading"><div><p class="greeting">My Garden</p><h1>Your plants</h1><p class="page-subtitle">Maintain personal plant records and notes.</p></div></div>
  <div class="plant-toolbar"><div></div><button class="primary-button" id="addPlantBtn" type="button">＋ Add plant</button></div>
  <div class="plant-grid" id="plantGrid"></div>`;

const historyView = document.getElementById("view-history");
historyView.innerHTML = `
  <div class="page-heading"><div><p class="greeting">Scan History</p><h1>Completed scans</h1><p class="page-subtitle">Only scans saved to your account are shown.</p></div></div>
  <div class="disease-toolbar"><input id="historySearch" type="search" placeholder="Search predictions or plants" aria-label="Search scan history"></div>
  <div class="prediction-list" id="historyList"></div>`;

document.getElementById("view-reminders").innerHTML = `
  <div class="page-heading"><div><p class="greeting">Reminders</p><h1>Plant care schedule</h1><p class="page-subtitle">Create personal follow-up tasks for your plants.</p></div></div>
  <form class="reminder-form" id="reminderForm">
    <input id="reminderTitle" required maxlength="120" placeholder="Reminder title">
    <select id="reminderType" required>
      <option value="">Reminder type</option><option>Watering</option><option>Fertilizer</option>
      <option>Inspection</option><option>Disease follow-up</option><option>Pruning</option><option>Seasonal care</option>
    </select>
    <input id="reminderDue" type="datetime-local" required>
    <button class="primary-button" type="submit">Add reminder</button>
  </form>
  <div class="reminder-list" id="reminderList"></div>`;

document.getElementById("view-doctor").innerHTML = `
  <div class="page-heading"><div><p class="greeting">AI Plant Doctor</p><h1>Ask a plant-care question</h1><p class="page-subtitle">Answers use the available disease records and general plant-care guidance.</p></div></div>
  <div class="chat-layout">
    <aside class="suggested-questions">
      <strong>Suggested questions</strong>
      <button type="button" data-question="Why are my tomato leaves turning yellow?">Why are tomato leaves yellow?</button>
      <button type="button" data-question="How can I prevent fungal infection?">Prevent fungal infection</button>
      <button type="button" data-question="How often should I water plants?">How often should I water?</button>
    </aside>
    <section class="chat-panel">
      <div class="chat-messages" id="chatMessages">
        <div class="chat-message assistant">Describe a symptom or ask a general plant-care question.</div>
      </div>
      <form class="chat-form" id="chatForm">
        <input id="chatInput" maxlength="1000" required placeholder="Ask Plant Doctor...">
        <button class="primary-button" type="submit">Send</button>
        <button class="text-button" type="button" id="clearChatBtn">Clear</button>
      </form>
    </section>
  </div>`;

document.getElementById("view-weather").innerHTML = `
  <div class="page-heading"><div><p class="greeting">Weather</p><h1>Weather-based plant care</h1><p class="page-subtitle">Use your location or enter coordinates manually.</p></div></div>
  <div class="weather-panel">
    <div class="weather-actions">
      <button class="primary-button" type="button" id="useLocationBtn">Use my location</button>
      <div class="coordinate-form">
        <input id="latitudeInput" type="number" min="-90" max="90" step="0.0001" placeholder="Latitude">
        <input id="longitudeInput" type="number" min="-180" max="180" step="0.0001" placeholder="Longitude">
        <button class="secondary-button" type="button" id="loadWeatherBtn">Check weather</button>
      </div>
    </div>
    <div id="weatherResult" class="weather-result">No weather data loaded.</div>
  </div>`;

const diseaseView = document.getElementById("view-disease");
diseaseView.innerHTML = `
  <div class="page-heading">
    <div><p class="greeting">Disease Library</p><h1>Supported plant conditions</h1><p class="page-subtitle">Information is linked to the model’s 54 known classes.</p></div>
  </div>
  <div class="disease-toolbar">
    <input id="diseaseSearch" type="search" placeholder="Search disease or plant" aria-label="Search disease or plant">
    <select id="diseaseCategory" aria-label="Filter by category">
      <option value="">All categories</option>
      <option>Healthy</option><option>Bacterial</option><option>Fungal</option><option>Viral</option>
      <option>Pest</option><option>Nutrient or toxicity</option><option>Environmental stress</option><option>Unclassified</option>
    </select>
  </div>
  <div class="disease-grid" id="diseaseGrid"><p class="page-subtitle">Loading disease records…</p></div>`;

async function loadDiseaseLibrary() {
  const grid = document.getElementById("diseaseGrid");
  const query = document.getElementById("diseaseSearch").value.trim();
  const category = document.getElementById("diseaseCategory").value;
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (category) params.set("category", category);
  try {
    const response = await fetch(`/api/diseases?${params}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load disease records.");
    grid.replaceChildren();
    if (!payload.diseases.length) {
      const empty = document.createElement("p");
      empty.className = "page-subtitle";
      empty.textContent = "No matching disease records found.";
      grid.appendChild(empty);
      return;
    }
    payload.diseases.forEach(disease => {
      const card = document.createElement("article");
      card.className = "disease-card";
      const categoryLabel = document.createElement("span");
      categoryLabel.className = "disease-category";
      categoryLabel.textContent = disease.disease_category;
      const title = document.createElement("h2");
      title.textContent = disease.disease_name;
      const plant = document.createElement("p");
      plant.textContent = `Affected plant: ${disease.affected_plant}`;
      const description = document.createElement("p");
      description.textContent = disease.description;
      card.append(categoryLabel, title, plant, description);
      grid.appendChild(card);
    });
  } catch (error) {
    grid.textContent = error.message;
  }
}
document.getElementById("diseaseSearch").addEventListener("input", loadDiseaseLibrary);
document.getElementById("diseaseCategory").addEventListener("change", loadDiseaseLibrary);

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.getElementById("toastRegion").appendChild(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  if (options.body && typeof options.body === "string") headers.set("Content-Type", "application/json");
  const response = await fetch(url, { ...options, headers });
  let payload = {};
  try { payload = await response.json(); } catch (error) { payload = {}; }
  if (!response.ok) throw new Error(payload.error || "Request failed.");
  return payload;
}

async function refreshSession() {
  try {
    const csrf = await apiFetch("/api/csrf");
    csrfToken = csrf.csrf_token;
    const payload = await apiFetch("/api/auth/me");
    currentUser = payload.user;
    updateProfile();
  } catch (error) {
    currentUser = null;
  }
}

function updateProfile() {
  const copy = document.querySelector(".profile-copy");
  const avatar = document.querySelector(".avatar");
  if (currentUser) {
    copy.innerHTML = `<strong>${escapeHtml(currentUser.name)}</strong><span>${escapeHtml(currentUser.email)}</span>`;
    avatar.textContent = currentUser.name.slice(0, 2).toUpperCase();
  } else {
    copy.innerHTML = "<strong>Guest grower</strong><span>Sign in to save records</span>";
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);
}

function switchView(name) {
  document.querySelectorAll(".view").forEach(view => view.classList.remove("active"));
  document.querySelectorAll("[data-view]").forEach(button => {
    if (button.classList.contains("nav-item") || button.closest(".bottom-nav")) {
      button.classList.toggle("active", button.dataset.view === name);
    }
  });
  const target = document.getElementById(`view-${name}`);
  if (target) target.classList.add("active");
  sidebar.classList.remove("mobile-open");
  sidebarOverlay.classList.remove("visible");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "disease") loadDiseaseLibrary();
  if (name === "garden") loadPlants();
  if (name === "history") loadHistory();
  if (name === "reminders") loadReminders();
}

document.addEventListener("click", event => {
  const button = event.target.closest("[data-view]");
  if (!button) return;
  event.preventDefault();
  switchView(button.dataset.view);
});

document.getElementById("sidebarToggle").addEventListener("click", () => {
  if (window.innerWidth <= 760) {
    sidebar.classList.remove("mobile-open");
    sidebarOverlay.classList.remove("visible");
  } else {
    sidebar.classList.toggle("collapsed");
  }
});

document.getElementById("mobileMenu").addEventListener("click", () => {
  sidebar.classList.add("mobile-open");
  sidebarOverlay.classList.add("visible");
});
sidebarOverlay.addEventListener("click", () => {
  sidebar.classList.remove("mobile-open");
  sidebarOverlay.classList.remove("visible");
});

const authDialog = document.getElementById("authDialog");
const plantDialog = document.getElementById("plantDialog");
document.getElementById("profileMenu").addEventListener("click", event => {
  if (event.target.closest(".icon-button")) return;
  if (currentUser) {
    if (confirm(`Log out ${currentUser.email}?`)) {
      apiFetch("/api/auth/logout", { method: "POST" }).then(() => {
        currentUser = null;
        updateProfile();
        showToast("Signed out.");
      }).catch(error => showToast(error.message, "error"));
    }
  } else {
    authDialog.showModal();
  }
});

function setAuthMode(mode) {
  authMode = mode;
  document.getElementById("loginTab").classList.toggle("active", mode === "login");
  document.getElementById("registerTab").classList.toggle("active", mode === "register");
  document.getElementById("authNameField").hidden = mode !== "register";
  document.getElementById("authPassword").autocomplete = mode === "login" ? "current-password" : "new-password";
  document.getElementById("authSubmit").textContent = mode === "login" ? "Log in" : "Create account";
}
document.getElementById("loginTab").addEventListener("click", () => setAuthMode("login"));
document.getElementById("registerTab").addEventListener("click", () => setAuthMode("register"));

document.getElementById("authForm").addEventListener("submit", async event => {
  event.preventEvent?.();
  event.preventDefault();
  const endpoint = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
  const body = {
    email: document.getElementById("authEmail").value,
    password: document.getElementById("authPassword").value
  };
  if (authMode === "register") body.name = document.getElementById("authName").value;
  try {
    const payload = await apiFetch(endpoint, { method: "POST", body: JSON.stringify(body) });
    csrfToken = payload.csrf_token;
    currentUser = payload.user;
    updateProfile();
    authDialog.close();
    showToast(authMode === "login" ? "Welcome back." : "Account created.");
  } catch (error) {
    showToast(error.message, "error");
  }
});

async function loadPlants() {
  const grid = document.getElementById("plantGrid");
  if (!currentUser) {
    grid.innerHTML = '<div class="feature-placeholder"><div><div class="empty-icon">♧</div><h1>Sign in to manage plants</h1><p>Create an account or log in to keep your garden private.</p></div></div>';
    return;
  }
  try {
    const payload = await apiFetch("/api/plants");
    grid.replaceChildren();
    if (!payload.plants.length) {
      grid.innerHTML = '<div class="feature-placeholder"><div><div class="empty-icon">♧</div><h1>No plants yet</h1><p>Add the first plant in your garden.</p></div></div>';
      return;
    }
    payload.plants.forEach(plant => {
      const card = document.createElement("article");
      card.className = "plant-card";
      card.innerHTML = `
        <span class="disease-category">${escapeHtml(plant.plant_type)}</span>
        <h2>${escapeHtml(plant.name)}</h2>
        <p>${plant.location ? escapeHtml(plant.location) : "Location not set"}</p>
        <p>${plant.planting_date ? `Planted ${escapeHtml(plant.planting_date)}` : "Planting date not set"}</p>
        <button class="text-button" type="button" data-delete-plant="${plant.id}">Delete</button>`;
      grid.appendChild(card);
    });
  } catch (error) {
    grid.textContent = error.message;
  }
}

document.getElementById("addPlantBtn").addEventListener("click", () => {
  if (!currentUser) {
    authDialog.showModal();
    return;
  }
  plantDialog.showModal();
});

document.getElementById("plantForm").addEventListener("submit", async event => {
  event.preventDefault();
  const body = {
    name: document.getElementById("plantName").value,
    plant_type: document.getElementById("plantType").value,
    planting_date: document.getElementById("plantDate").value,
    location: document.getElementById("plantLocation").value,
    notes: document.getElementById("plantNotes").value
  };
  try {
    await apiFetch("/api/plants", { method: "POST", body: JSON.stringify(body) });
    plantDialog.close();
    event.target.reset();
    showToast("Plant added.");
    loadPlants();
  } catch (error) {
    showToast(error.message, "error");
  }
});

document.addEventListener("click", async event => {
  const deleteButton = event.target.closest("[data-delete-plant]");
  if (!deleteButton) return;
  if (!confirm("Delete this plant?")) return;
  try {
    await apiFetch(`/api/plants/${deleteButton.dataset.deletePlant}`, { method: "DELETE" });
    showToast("Plant deleted.");
    loadPlants();
  } catch (error) {
    showToast(error.message, "error");
  }
});

document.querySelectorAll("[data-question]").forEach(button => {
  button.addEventListener("click", () => {
    document.getElementById("chatInput").value = button.dataset.question;
    document.getElementById("chatInput").focus();
  });
});

document.getElementById("chatForm").addEventListener("submit", async event => {
  event.preventDefault();
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;
  const messages = document.getElementById("chatMessages");
  const userBubble = document.createElement("div");
  userBubble.className = "chat-message user";
  userBubble.textContent = message;
  messages.appendChild(userBubble);
  input.value = "";

  const typing = document.createElement("div");
  typing.className = "chat-message assistant typing";
  typing.textContent = "Plant Doctor is thinking...";
  messages.appendChild(typing);
  try {
    const payload = await apiFetch("/api/doctor/chat", {
      method: "POST",
      body: JSON.stringify({ message })
    });
    typing.remove();
    const assistantBubble = document.createElement("div");
    assistantBubble.className = "chat-message assistant";
    assistantBubble.textContent = payload.answer;
    messages.appendChild(assistantBubble);
    messages.scrollTop = messages.scrollHeight;
  } catch (error) {
    typing.remove();
    showToast(error.message, "error");
  }
});

document.getElementById("clearChatBtn").addEventListener("click", async () => {
  try {
    await apiFetch("/api/doctor/clear", { method: "POST" });
  } catch (error) {
    showToast(error.message, "error");
  }
  document.getElementById("chatMessages").innerHTML =
    '<div class="chat-message assistant">Describe a symptom or ask a general plant-care question.</div>';
});

async function loadWeather(latitude, longitude) {
  const result = document.getElementById("weatherResult");
  result.textContent = "Loading current weather...";
  try {
    const payload = await apiFetch(`/api/weather?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}`);
    result.innerHTML = `
      <div class="weather-grid">
        <article><span>Temperature</span><strong>${payload.temperature_c ?? "—"}°C</strong></article>
        <article><span>Humidity</span><strong>${payload.humidity_percent ?? "—"}%</strong></article>
        <article><span>Rain</span><strong>${payload.rain_mm ?? "—"} mm</strong></article>
      </div>
      <div class="weather-guidance"><strong>Care guidance</strong><p>${escapeHtml(payload.guidance)}</p><small>Source: ${escapeHtml(payload.source)}</small></div>`;
  } catch (error) {
    result.textContent = error.message;
  }
}

document.getElementById("loadWeatherBtn").addEventListener("click", () => {
  const latitude = document.getElementById("latitudeInput").value;
  const longitude = document.getElementById("longitudeInput").value;
  if (!latitude || !longitude) {
    showToast("Enter both latitude and longitude.", "error");
    return;
  }
  loadWeather(latitude, longitude);
});

document.getElementById("useLocationBtn").addEventListener("click", () => {
  if (!navigator.geolocation) {
    showToast("Location is unavailable. Enter coordinates manually.", "error");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    position => {
      document.getElementById("latitudeInput").value = position.coords.latitude.toFixed(4);
      document.getElementById("longitudeInput").value = position.coords.longitude.toFixed(4);
      loadWeather(position.coords.latitude, position.coords.longitude);
    },
    () => showToast("Location permission was not granted. Enter coordinates manually.", "error")
  );
});

document.getElementById("uploadFromOverview").addEventListener("click", () => {
  switchView("scanner");
  galleryInput.click();
});

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  cameraPreview.hidden = true;
  cameraActions.hidden = true;
  cameraPreview.srcObject = null;
}

function resetSelection() {
  stopCamera();
  selectedFile = null;
  galleryInput.value = "";
  cameraInput.value = "";
  cameraHelp.hidden = true;
  analysisMessage.hidden = true;
  analysisMessage.classList.remove("error");
  preview.removeAttribute("src");
  preview.hidden = true;
  placeholder.hidden = false;
  fileName.textContent = "No image selected";
  analyzeBtn.disabled = true;
  resetBtn.disabled = true;
  result.hidden = true;
}

function chooseFile(file) {
  if (!file) return;
  stopCamera();
  cameraHelp.hidden = true;
  analysisMessage.hidden = true;
  analysisMessage.classList.remove("error");
  if (!file.type.startsWith("image/")) {
    showToast("Please choose an image file.", "error");
    return;
  }
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    showToast("Please upload JPG, JPEG, PNG or WEBP.", "error");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast("Please choose an image smaller than 10 MB.", "error");
    return;
  }
  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  preview.hidden = false;
  placeholder.hidden = true;
  fileName.textContent = file.name || "Camera photo selected";
  analyzeBtn.disabled = false;
  resetBtn.disabled = false;
  result.hidden = true;
}

galleryInput.addEventListener("change", event => {
  chooseFile(event.target.files[0]);
  event.target.value = "";
});
cameraInput.addEventListener("change", event => {
  chooseFile(event.target.files[0]);
  event.target.value = "";
});
resetBtn.addEventListener("click", resetSelection);

["dragenter", "dragover"].forEach(type => {
  dropzone.addEventListener(type, event => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
});
["dragleave", "drop"].forEach(type => {
  dropzone.addEventListener(type, event => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  });
});
dropzone.addEventListener("drop", event => chooseFile(event.dataTransfer.files[0]));

document.getElementById("cameraBtn").addEventListener("click", async () => {
  cameraHelp.hidden = true;
  if (window.isSecureContext === false) {
    cameraHelp.textContent = "Live camera needs a secure HTTPS link. Open this site in Safari or Chrome, or use phone camera capture.";
    cameraHelp.hidden = false;
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraHelp.textContent = "Live camera is unavailable in this browser. Use phone camera capture or upload an image.";
    cameraHelp.hidden = false;
    return;
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false
    });
    cameraPreview.srcObject = cameraStream;
    cameraPreview.hidden = false;
    placeholder.hidden = true;
    preview.hidden = true;
    cameraActions.hidden = false;
    await cameraPreview.play();
  } catch (error) {
    stopCamera();
    if (!selectedFile) placeholder.hidden = false;
    console.warn("Live camera initialization failed:", error);
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      cameraHelp.textContent = "Camera access is blocked. Allow Camera for this site in your browser settings, then reload. Or use phone camera capture or upload.";
    } else if (error.name === "NotFoundError") {
      cameraHelp.textContent = "No camera was found. Use phone camera capture or upload an image.";
    } else if (error.name === "NotReadableError") {
      cameraHelp.textContent = "The camera is busy. Close other apps using it, then try again or use phone camera capture.";
    } else {
      cameraHelp.textContent = "Could not open live camera. Use phone camera capture or upload an image.";
    }
    cameraHelp.hidden = false;
  }
});

document.getElementById("deviceCameraBtn").addEventListener("click", () => cameraInput.click());

document.getElementById("captureBtn").addEventListener("click", () => {
  const width = cameraPreview.videoWidth;
  const height = cameraPreview.videoHeight;
  if (!width || !height) {
    showToast("The camera is still starting. Try again in a moment.", "error");
    return;
  }
  cameraCanvas.width = width;
  cameraCanvas.height = height;
  cameraCanvas.getContext("2d").drawImage(cameraPreview, 0, 0, width, height);
  cameraCanvas.toBlob(blob => {
    if (!blob) {
      cameraHelp.textContent = "Could not capture the photo. Try the phone camera button or upload an image.";
      cameraHelp.hidden = false;
      return;
    }
    stopCamera();
    chooseFile(new File([blob], "camera-photo.jpg", { type: "image/jpeg" }));
  }, "image/jpeg", 0.92);
});

document.getElementById("closeCameraBtn").addEventListener("click", () => {
  stopCamera();
  if (!selectedFile) placeholder.hidden = false;
});

function replaceTextList(elementId, items) {
  const list = document.getElementById(elementId);
  list.replaceChildren();
  (items || []).forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

async function loadHistory() {
  const list = document.getElementById("historyList");
  if (!currentUser) {
    list.innerHTML = '<div class="feature-placeholder"><div><div class="empty-icon">↶</div><h1>Sign in to view history</h1><p>Saved scan records are private to your account.</p></div></div>';
    return;
  }
  const query = document.getElementById("historySearch").value.trim();
  try {
    const payload = await apiFetch(`/api/scans${query ? `?q=${encodeURIComponent(query)}` : ""}`);
    list.replaceChildren();
    if (!payload.scans.length) {
      list.innerHTML = '<div class="feature-placeholder"><div><div class="empty-icon">↶</div><h1>No saved scans</h1><p>Complete an analysis and save it to see it here.</p></div></div>';
      return;
    }
    payload.scans.forEach(scan => {
      const row = document.createElement("article");
      row.className = "plant-card";
      row.innerHTML = `
        <span class="disease-category">${escapeHtml(scan.status)}</span>
        <h2>${escapeHtml(scan.prediction)}</h2>
        <p>${escapeHtml(scan.scan_date || scan.created_at)}</p>
        <p><strong>${Number(scan.confidence).toFixed(1)}% confidence</strong></p>
        <button class="text-button" type="button" data-delete-scan="${scan.id}">Delete</button>`;
      list.appendChild(row);
    });
  } catch (error) {
    list.textContent = error.message;
  }
}

document.addEventListener("input", event => {
  if (event.target.id === "historySearch") loadHistory();
});

document.addEventListener("click", async event => {
  const deleteButton = event.target.closest("[data-delete-scan]");
  if (!deleteButton) return;
  if (!confirm("Delete this scan record?")) return;
  try {
    await apiFetch(`/api/scans/${deleteButton.dataset.deleteScan}`, { method: "DELETE" });
    showToast("Scan deleted.");
    loadHistory();
  } catch (error) {
    showToast(error.message, "error");
  }
});

async function loadReminders() {
  const list = document.getElementById("reminderList");
  if (!currentUser) {
    list.innerHTML = '<div class="feature-placeholder"><div><div class="empty-icon">◷</div><h1>Sign in to use reminders</h1><p>Reminders are stored privately with your account.</p></div></div>';
    return;
  }
  try {
    const payload = await apiFetch("/api/reminders");
    list.replaceChildren();
    if (!payload.reminders.length) {
      list.innerHTML = '<div class="feature-placeholder"><div><div class="empty-icon">◷</div><h1>No reminders yet</h1><p>Add a watering, inspection, or care task above.</p></div></div>';
      return;
    }
    payload.reminders.forEach(reminder => {
      const row = document.createElement("article");
      row.className = `reminder-card${reminder.completed ? " completed" : ""}`;
      row.innerHTML = `
        <span class="disease-category">${escapeHtml(reminder.reminder_type)}</span>
        <h2>${escapeHtml(reminder.title)}</h2>
        <p>${escapeHtml(reminder.due_at)}</p>
        <div class="account-row">
          <button class="text-button" type="button" data-reminder-complete="${reminder.id}" data-completed="${reminder.completed ? "0" : "1"}">${reminder.completed ? "Mark active" : "Mark complete"}</button>
          <button class="text-button" type="button" data-delete-reminder="${reminder.id}">Delete</button>
        </div>`;
      list.appendChild(row);
    });
  } catch (error) {
    list.textContent = error.message;
  }
}

document.getElementById("reminderForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!currentUser) {
    document.getElementById("authDialog").showModal();
    return;
  }
  try {
    await apiFetch("/api/reminders", {
      method: "POST",
      body: JSON.stringify({
        title: document.getElementById("reminderTitle").value,
        reminder_type: document.getElementById("reminderType").value,
        due_at: document.getElementById("reminderDue").value,
      })
    });
    event.target.reset();
    showToast("Reminder added.");
    loadReminders();
  } catch (error) {
    showToast(error.message, "error");
  }
});

document.addEventListener("click", async event => {
  const complete = event.target.closest("[data-reminder-complete]");
  if (complete) {
    try {
      await apiFetch(`/api/reminders/${complete.dataset.reminderComplete}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: complete.dataset.completed === "1" })
      });
      loadReminders();
    } catch (error) {
      showToast(error.message, "error");
    }
  }
  const remove = event.target.closest("[data-delete-reminder]");
  if (remove) {
    if (!confirm("Delete this reminder?")) return;
    try {
      await apiFetch(`/api/reminders/${remove.dataset.deleteReminder}`, { method: "DELETE" });
      showToast("Reminder deleted.");
      loadReminders();
    } catch (error) {
      showToast(error.message, "error");
    }
  }
});

function addRecentScan(payload) {
  recentScans.unshift({
    name: payload.plant_diagnosis,
    status: payload.status,
    confidence: payload.confidence,
    date: new Date()
  });
  scanCount += 1;
  if (payload.status === "Healthy-class prediction") healthyCount += 1;
  if (payload.status === "Possible disease detected") diseaseCount += 1;
  document.getElementById("overviewScanCount").textContent = scanCount;
  document.getElementById("healthyCount").textContent = healthyCount;
  document.getElementById("diseaseCount").textContent = diseaseCount;

  const recentEmpty = document.getElementById("recentEmpty");
  recentEmpty.innerHTML = recentScans.slice(0, 4).map(scan => `
    <div class="prediction-row">
      <span><strong>${scan.name}</strong><br><small>${scan.status}</small></span>
      <strong>${scan.confidence}%</strong>
    </div>`).join("");
  recentEmpty.className = "prediction-list";
}

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  const formData = new FormData();
  formData.append("image", selectedFile);
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing…";
  analysisMessage.textContent = "On the free demo, the first scan after inactivity may take 50+ seconds. Keep this page open.";
  analysisMessage.classList.remove("error");
  analysisMessage.hidden = false;
  result.hidden = true;

  try {
    const headers = csrfToken ? { "X-CSRF-Token": csrfToken } : {};
    const response = await fetch("/api/analyze", { method: "POST", body: formData, headers });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Analysis failed.");

    analysisMessage.hidden = true;
    document.getElementById("resultTitle").textContent = "Analysis complete";
    document.getElementById("resultStatus").textContent = payload.status;
    document.getElementById("resultConfidence").textContent = `${payload.confidence}% confidence`;
    document.getElementById("resultDiagnosis").textContent = payload.plant_diagnosis;
    document.getElementById("resultNote").textContent = payload.note;
    lastPrediction = payload;

    const qualityBanner = document.getElementById("qualityBanner");
    if (payload.image_quality) {
      qualityBanner.hidden = false;
      qualityBanner.className = `quality-banner ${payload.image_quality.status}`;
      qualityBanner.textContent = `${payload.image_quality.label}. ${payload.image_quality.message}`;
    } else {
      qualityBanner.hidden = true;
    }

    document.getElementById("severityValue").textContent = payload.severity || "Unknown";
    document.getElementById("severityBasis").textContent = payload.severity_basis || "Severity requires visual examination.";

    let disease = null;
    if (payload.raw_label) {
      try {
        const diseaseResponse = await fetch(`/api/diseases/${encodeURIComponent(payload.raw_label)}`);
        if (diseaseResponse.ok) disease = await diseaseResponse.json();
      } catch (error) {
        disease = null;
      }
    }

    document.getElementById("reportDiagnosis").textContent = payload.plant_diagnosis;
    document.getElementById("reportDescription").textContent =
      disease?.description || "Detailed verified disease information is unavailable for this model result.";
    replaceTextList("reportSymptoms", disease?.symptoms || [
      "Visible symptoms could not be confirmed automatically."
    ]);
    replaceTextList("reportCauses", disease?.causes || [
      "Possible causes require expert or on-site confirmation."
    ]);
    replaceTextList("reportTreatment", disease?.treatment || [
      "Use general plant-care practices and consult a qualified agricultural professional."
    ]);
    replaceTextList("reportPrevention", disease?.prevention || [
      "Inspect plants regularly and maintain appropriate watering and airflow."
    ]);
    replaceTextList("reportSources", disease?.reference_sources || [
      "Plantulus Doctor model card"
    ]);

    const list = document.getElementById("topPredictions");
    list.replaceChildren();
    (payload.top_predictions || []).forEach(item => {
      const row = document.createElement("div");
      row.className = "prediction-row";
      const name = document.createElement("span");
      name.textContent = item.name;
      const score = document.createElement("strong");
      score.textContent = `${item.confidence}%`;
      row.append(name, score);
      list.appendChild(row);
    });

    result.hidden = false;
    addRecentScan(payload);
    showToast("Analysis completed.");
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    analysisMessage.textContent = error.message;
    analysisMessage.classList.add("error");
    analysisMessage.hidden = false;
    showToast(error.message, "error");
  } finally {
    analyzeBtn.disabled = !selectedFile;
    analyzeBtn.innerHTML = 'Analyze leaf <span>→</span>';
  }
});

const languageLabels = {
  en: {
    code: "EN",
    nav: ["Overview", "AI Plant Scanner", "My Garden", "Disease Library", "AI Plant Doctor", "Scan History", "Reminders", "Weather", "Reports", "Settings"],
    greeting: "Welcome to PlantCare AI"
  },
  hi: {
    code: "हि",
    nav: ["अवलोकन", "एआई पौधा स्कैनर", "मेरा बगीचा", "रोग लाइब्रेरी", "एआई प्लांट डॉक्टर", "स्कैन इतिहास", "रिमाइंडर", "मौसम", "रिपोर्ट", "सेटिंग्स"],
    greeting: "PlantCare AI में आपका स्वागत है"
  },
  mr: {
    code: "म",
    nav: ["आढावा", "एआई वनस्पती स्कॅनर", "माझे बाग", "रोग संग्रह", "एआई प्लांट डॉक्टर", "स्कॅन इतिहास", "आठवणी", "हवामान", "अहवाल", "सेटिंग्ज"],
    greeting: "PlantCare AI मध्ये स्वागत आहे"
  }
};
let currentLanguage = "en";

function applyLanguage(language) {
  currentLanguage = language;
  document.documentElement.lang = language === "en" ? "en" : language === "hi" ? "hi" : "mr";
  document.querySelector("#languageButton span").textContent = languageLabels[language].code;
  document.querySelectorAll(".nav-item").forEach((item, index) => {
    const label = item.querySelector("span:last-child");
    if (label) label.textContent = languageLabels[language].nav[index];
  });
  const heading = document.querySelector("#view-overview .page-heading h1");
  if (heading) heading.textContent = languageLabels[language].greeting;
  document.querySelectorAll(".bottom-nav small").forEach((label, index) => {
    if (languageLabels[language].nav[index]) label.textContent = languageLabels[language].nav[index];
  });
  showToast(`Language changed to ${language === "en" ? "English" : language === "hi" ? "Hindi" : "Marathi"}.`);
}

document.getElementById("languageButton").addEventListener("click", () => {
  const next = currentLanguage === "en" ? "hi" : currentLanguage === "hi" ? "mr" : "en";
  applyLanguage(next);
});

document.getElementById("saveScanBtn").addEventListener("click", async () => {
  if (!lastPrediction) return;
  if (!currentUser) {
    authDialog.showModal();
    return;
  }
  try {
    await apiFetch("/api/scans", {
      method: "POST",
      body: JSON.stringify({
        prediction: lastPrediction.plant_diagnosis,
        status: lastPrediction.status,
        confidence: lastPrediction.confidence,
        low_confidence: lastPrediction.low_confidence,
        raw_label: lastPrediction.raw_label,
        top_predictions: lastPrediction.top_predictions,
        image_quality: lastPrediction.image_quality,
        scan_date: lastPrediction.scan_date
      })
    });
    showToast("Scan saved to your account.");
  } catch (error) {
    showToast(error.message, "error");
  }
});

document.getElementById("globalSearch").addEventListener("keydown", event => {
  if (event.key === "Enter") {
    const query = event.currentTarget.value.trim();
    if (query) showToast(`Search is ready for “${query}” after the library is implemented.`);
  }
});

refreshSession();
