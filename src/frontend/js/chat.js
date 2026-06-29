const state = {
  userId: localStorage.getItem("algorag.userId") || "demo-user",
  projects: [],
  activeProjectId: localStorage.getItem("algorag.activeProjectId") || "",
  sessionId: localStorage.getItem("algorag.sessionId") || crypto.randomUUID(),
  isIndexed: false
};

localStorage.setItem("algorag.sessionId", state.sessionId);

const $ = (id) => document.getElementById(id);

const el = {
  userId: $("userIdInput"),
  projectSelector: $("projectSelector"),
  activeProjectName: $("activeProjectName"),
  chatLog: $("chatLog"),
  chatForm: $("chatForm"),
  questionInput: $("questionInput"),
  sendBtn: $("sendBtn"),
  
  // Status banner
  projectStatusBanner: $("projectStatusBanner"),
  statusIcon: $("statusIcon"),
  statusTitle: $("statusTitle"),
  statusDetail: $("statusDetail")
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
    await checkIndexStatus();
  } catch (err) {
    console.error("Failed to load projects", err);
  }
}

function renderProjects() {
  el.projectSelector.innerHTML = "";
  if (state.projects.length === 0) {
    el.projectSelector.innerHTML = `<option value="">No projects found</option>`;
    el.activeProjectName.textContent = "No Project";
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
      el.activeProjectName.textContent = p.name;
    }
    el.projectSelector.appendChild(opt);
  });

  if (!foundActive && state.projects.length > 0) {
    state.activeProjectId = state.projects[0].id;
    localStorage.setItem("algorag.activeProjectId", state.activeProjectId);
    el.projectSelector.value = state.activeProjectId;
    el.activeProjectName.textContent = state.projects[0].name;
  }
}

function getActiveProjectNumericId() {
  const p = state.projects.find(x => x.id === state.activeProjectId);
  return p ? p.project_id : null;
}

// Check Index Status
async function checkIndexStatus() {
  const pId = getActiveProjectNumericId();
  if (!pId) {
    setStatus("warning", "No Project", "Create or select a project in the Admin Dashboard.");
    return;
  }

  try {
    const payload = await api(`/api/v1/nlp/index/info/${pId}`, { method: "GET" });
    const info = payload.collection_info || {};
    const records = info.record_count || 0;

    if (records > 0) {
      state.isIndexed = true;
      setStatus("success", "Ready", `${records} chunks indexed. You can ask questions.`);
      el.questionInput.disabled = false;
      el.sendBtn.disabled = false;
    } else {
      state.isIndexed = false;
      setStatus("warning", "Not Ready", "No documents indexed. Upload files in the Admin Dashboard.");
      el.questionInput.disabled = true;
      el.sendBtn.disabled = true;
    }
  } catch (err) {
    state.isIndexed = false;
    setStatus("error", "Error", "Failed to check project status.");
    el.questionInput.disabled = true;
    el.sendBtn.disabled = true;
  }
}

function setStatus(type, title, detail) {
  el.projectStatusBanner.style.display = "block";
  el.statusTitle.textContent = title;
  el.statusDetail.textContent = detail;
  
  if (type === "success") {
    el.statusIcon.textContent = "check_circle";
    el.statusIcon.style.color = "var(--accent)";
    el.projectStatusBanner.style.borderColor = "var(--accent)";
  } else if (type === "warning") {
    el.statusIcon.textContent = "info";
    el.statusIcon.style.color = "#fbbf24";
    el.projectStatusBanner.style.borderColor = "#fbbf24";
  } else {
    el.statusIcon.textContent = "error";
    el.statusIcon.style.color = "#ef4444";
    el.projectStatusBanner.style.borderColor = "#ef4444";
  }
}

// Chat UI functions
function addMessage(role, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;
  
  const avatarDiv = document.createElement("div");
  avatarDiv.className = "avatar";
  
  const iconSpan = document.createElement("span");
  iconSpan.className = "material-symbols-outlined";
  iconSpan.textContent = role === "user" ? "person" : "smart_toy";
  avatarDiv.appendChild(iconSpan);
  
  const bubbleDiv = document.createElement("div");
  bubbleDiv.className = "message-bubble";
  bubbleDiv.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  
  msgDiv.appendChild(avatarDiv);
  msgDiv.appendChild(bubbleDiv);
  
  el.chatLog.appendChild(msgDiv);
  el.chatLog.scrollTop = el.chatLog.scrollHeight;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

let typingIndicator = null;
function showTyping() {
  typingIndicator = document.createElement("div");
  typingIndicator.className = "message assistant";
  typingIndicator.innerHTML = `
    <div class="avatar"><span class="material-symbols-outlined">smart_toy</span></div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  el.chatLog.appendChild(typingIndicator);
  el.chatLog.scrollTop = el.chatLog.scrollHeight;
}

function hideTyping() {
  if (typingIndicator) {
    typingIndicator.remove();
    typingIndicator = null;
  }
}

// Ask Question
el.chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = el.questionInput.value.trim();
  if (!text) return;
  
  const pId = getActiveProjectNumericId();
  if (!pId) return;

  addMessage("user", text);
  el.questionInput.value = "";
  el.questionInput.disabled = true;
  el.sendBtn.disabled = true;
  
  showTyping();

  try {
    const payload = await api(`/api/v1/nlp/index/answer/${pId}`, {
      method: "POST",
      body: JSON.stringify({
        text,
        limit: 12,
        session_id: state.sessionId,
      }),
    });

    hideTyping();
    addMessage("assistant", payload.answer || "No answer returned.");
  } catch (error) {
    hideTyping();
    addMessage("assistant", `Error: ${error.message === "rag_no_context" ? "Documents are not indexed yet." : error.message}`);
  } finally {
    el.questionInput.disabled = false;
    el.sendBtn.disabled = false;
    el.questionInput.focus();
  }
});

// Allow Enter to submit, Shift+Enter for new line
el.questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!el.sendBtn.disabled) {
      el.chatForm.dispatchEvent(new Event("submit"));
    }
  }
});

// Event Listeners
el.userId.addEventListener("change", () => {
  state.userId = el.userId.value.trim() || "demo-user";
  localStorage.setItem("algorag.userId", state.userId);
  loadProjects();
});

el.projectSelector.addEventListener("change", () => {
  state.activeProjectId = el.projectSelector.value;
  localStorage.setItem("algorag.activeProjectId", state.activeProjectId);
  const p = state.projects.find(x => x.id === state.activeProjectId);
  el.activeProjectName.textContent = p ? p.name : "";
  checkIndexStatus();
});

// Init
el.userId.value = state.userId;
loadProjects();
