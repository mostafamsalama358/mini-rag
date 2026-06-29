const state = {
  userId: localStorage.getItem("algorag.userId") || "demo-user",
  projects: [],
  activeProjectId: localStorage.getItem("algorag.activeProjectId") || ""
};

const $ = (id) => document.getElementById(id);

// Elements
const el = {
  userId: $("userIdInput"),
  projectSelector: $("projectSelector"),
  createProjectForm: $("createProjectForm"),
  newProjectName: $("newProjectName"),
  createProjectMsg: $("createProjectMsg"),
  uploadArea: $("uploadArea"),
  fileInput: $("fileInput"),
  uploadStatus: $("uploadStatus"),
  
  // Stats
  statFiles: $("statFiles"),
  statQueries: $("statQueries"),
  statScore: $("statScore"),
  statOcr: $("statOcr"),
  statQuota: $("statQuota"),
  quotaBar: $("quotaBar"),

  // Modal
  metadataModal: $("metadataModal"),
  saveMetadataBtn: $("saveMetadataBtn"),
  skipMetadataBtn: $("skipMetadataBtn"),
  metadataTagsList: $("metadataTagsList")
};

function headers(json = true) {
  const result = { "X-User-Id": state.userId };
  if (json) result["Content-Type"] = "application/json";
  return result;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? headers(false) : headers(true)),
      ...(options.headers || {}),
    },
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || payload.signal || response.statusText;
    throw new Error(message);
  }

  return payload;
}

// Fetch Projects
async function loadProjects() {
  try {
    const payload = await api("/api/v1/projects");
    state.projects = payload.projects || [];
    renderProjects();
    updateMockStats();
  } catch (err) {
    console.error("Failed to load projects", err);
    el.projectSelector.innerHTML = `<option value="">Error loading projects</option>`;
  }
}

function renderProjects() {
  el.projectSelector.innerHTML = "";
  if (state.projects.length === 0) {
    el.projectSelector.innerHTML = `<option value="">No projects found</option>`;
    return;
  }
  
  let foundActive = false;
  state.projects.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    if (p.id === state.activeProjectId) {
      opt.selected = true;
      foundActive = true;
    }
    el.projectSelector.appendChild(opt);
  });

  if (!foundActive && state.projects.length > 0) {
    state.activeProjectId = state.projects[0].id;
    localStorage.setItem("algorag.activeProjectId", state.activeProjectId);
    el.projectSelector.value = state.activeProjectId;
  }
}

// Create Project
el.createProjectForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = el.newProjectName.value.trim();
  if (!name) return;

  el.createProjectForm.querySelector("button").disabled = true;
  el.createProjectMsg.textContent = "Creating...";

  try {
    const payload = await api("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    
    state.activeProjectId = payload.project.id;
    localStorage.setItem("algorag.activeProjectId", state.activeProjectId);
    el.newProjectName.value = "";
    el.createProjectMsg.textContent = "Project created successfully!";
    el.createProjectMsg.style.color = "var(--accent)";
    
    await loadProjects();
    setTimeout(() => { el.createProjectMsg.textContent = ""; }, 3000);
  } catch (err) {
    el.createProjectMsg.textContent = `Error: ${err.message}`;
    el.createProjectMsg.style.color = "#ef4444";
  } finally {
    el.createProjectForm.querySelector("button").disabled = false;
  }
});

// User ID Change
el.userId.addEventListener("change", () => {
  state.userId = el.userId.value.trim() || "demo-user";
  localStorage.setItem("algorag.userId", state.userId);
  loadProjects();
});

// Project Selection Change
el.projectSelector.addEventListener("change", () => {
  state.activeProjectId = el.projectSelector.value;
  localStorage.setItem("algorag.activeProjectId", state.activeProjectId);
  updateMockStats();
});

// File Upload Logic
el.uploadArea.addEventListener("click", () => el.fileInput.click());

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  el.uploadArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
  el.uploadArea.addEventListener(eventName, () => el.uploadArea.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
  el.uploadArea.addEventListener(eventName, () => el.uploadArea.classList.remove('dragover'), false);
});

el.uploadArea.addEventListener('drop', (e) => {
  const dt = e.dataTransfer;
  const files = dt.files;
  handleFiles(files);
});

el.fileInput.addEventListener('change', function() {
  handleFiles(this.files);
});

function getActiveProjectNumericId() {
  const p = state.projects.find(x => x.id === state.activeProjectId);
  return p ? p.project_id : null;
}

async function handleFiles(files) {
  if (files.length === 0) return;
  const pId = getActiveProjectNumericId();
  if (!pId) {
    alert("Please select or create a project first.");
    return;
  }

  el.uploadStatus.textContent = `Uploading ${files.length} file(s)...`;
  
  state.lastUploadedFiles = [];
  try {
    for (let i = 0; i < files.length; i++) {
      const form = new FormData();
      form.append("file", files[i]);
      const res = await api(`/api/v1/data/upload/${pId}`, { method: "POST", body: form });
      if (res.asset_name) {
        state.lastUploadedFiles.push(res.asset_name);
      } else {
        // Fallback just in case
        state.lastUploadedFiles.push(files[i].name);
      }
    }
    
    el.uploadStatus.textContent = "Generating metadata suggestions...";
    
    // Fetch suggestions
    const suggestRes = await api(`/api/v1/data/suggest-metadata/${pId}`, {
      method: "POST",
      body: JSON.stringify({ file_names: state.lastUploadedFiles }),
    });

    const tags = suggestRes.tags || [];
    if (tags.length > 0) {
      el.metadataTagsList.innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join('');
      el.uploadStatus.textContent = "Please review suggested metadata.";
      showMetadataPopup();
    } else {
      await triggerProcessAndPush(pId);
    }

  } catch (err) {
    el.uploadStatus.textContent = `Error: ${err.message}`;
    el.uploadStatus.style.color = "#ef4444";
  }
}

async function triggerProcessAndPush(pId) {
  el.uploadStatus.textContent = "Processing files...";
  try {
    await api(`/api/v1/data/process-and-push/${pId}`, {
      method: "POST",
      body: JSON.stringify({ do_reset: 0 }),
    });
    el.uploadStatus.textContent = "Upload & Processing triggered successfully!";
  } catch (err) {
    el.uploadStatus.textContent = `Error: ${err.message}`;
    el.uploadStatus.style.color = "#ef4444";
  }
}

// Metadata Popup Logic
function showMetadataPopup() {
  el.metadataModal.classList.add("active");
  // Reset tags
  const tags = el.metadataTagsList.querySelectorAll('.tag');
  tags.forEach(t => t.classList.remove('selected'));
  
  // Add click toggle
  tags.forEach(t => {
    t.onclick = () => t.classList.toggle('selected');
  });
}

function hideMetadataPopup() {
  el.metadataModal.classList.remove("active");
}

el.skipMetadataBtn.addEventListener("click", async () => {
  hideMetadataPopup();
  const pId = getActiveProjectNumericId();
  if (pId) await triggerProcessAndPush(pId);
});

el.saveMetadataBtn.addEventListener("click", async () => {
  const selected = Array.from(el.metadataTagsList.querySelectorAll('.tag.selected')).map(t => t.textContent);
  hideMetadataPopup();
  
  const pId = getActiveProjectNumericId();
  if (pId) {
    try {
      if (selected.length > 0) {
        el.uploadStatus.textContent = "Applying metadata...";
        await api(`/api/v1/data/update-metadata/${pId}`, {
          method: "POST",
          body: JSON.stringify({ file_names: state.lastUploadedFiles, tags: selected }),
        });
      }
      await triggerProcessAndPush(pId);
    } catch(err) {
      el.uploadStatus.textContent = `Error: ${err.message}`;
      el.uploadStatus.style.color = "#ef4444";
    }
  }
});


// Mock Statistics
function updateMockStats() {
  if (!state.activeProjectId) {
    el.statFiles.textContent = "0";
    el.statQueries.textContent = "0";
    el.statScore.textContent = "0.0";
    el.statOcr.textContent = "0";
    el.statQuota.textContent = "0 / 100k tokens (0%)";
    el.quotaBar.style.width = "0%";
    return;
  }

  // Generate deterministic mock data based on project ID
  const hash = state.activeProjectId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  
  const files = (hash % 50) + 1;
  const queries = (hash % 1000) + 20;
  const score = (0.7 + ((hash % 30) / 100)).toFixed(2); // e.g. 0.70 to 0.99
  const ocr = (hash % 200) + 5;
  const quotaUsed = (hash % 80000) + 5000;
  const quotaTotal = 100000;
  const quotaPercent = Math.round((quotaUsed / quotaTotal) * 100);

  // Animate counters
  animateValue(el.statFiles, 0, files, 1000);
  animateValue(el.statQueries, 0, queries, 1000);
  animateValue(el.statOcr, 0, ocr, 1000);
  
  el.statScore.textContent = score;
  
  el.statQuota.textContent = `${quotaUsed.toLocaleString()} / ${quotaTotal.toLocaleString()} tokens (${quotaPercent}%)`;
  
  // Trigger reflow for animation
  setTimeout(() => {
    el.quotaBar.style.width = `${quotaPercent}%`;
  }, 100);
}

function animateValue(obj, start, end, duration) {
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    obj.innerHTML = Math.floor(progress * (end - start) + start);
    if (progress < 1) {
      window.requestAnimationFrame(step);
    }
  };
  window.requestAnimationFrame(step);
}

// Init
el.userId.value = state.userId;
loadProjects();
