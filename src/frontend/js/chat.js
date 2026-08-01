const state = {
  userId: localStorage.getItem("algorag.userId") || "demo-user",
  projects: [],
  activeProjectId: localStorage.getItem("algorag.activeProjectId") || "",
  sessionId: localStorage.getItem("algorag.sessionId") || crypto.randomUUID(),
  isIndexed: false,
  selectedSkillId: localStorage.getItem("algorag.selectedSkillId") || "",
  skills: [],
};

const DEFAULT_WELCOME = {
  en: "Hello! Select a project from the sidebar to see domain-specific guidance, then ask about your indexed documents.",
  ar: "مرحباً! اختر مشروعاً من القائمة لعرض تعريف المجال، ثم اسأل عن المستندات المفهرسة.",
};

function uiLanguage() {
  const lang = (navigator.language || "en").toLowerCase();
  return lang.startsWith("ar") ? "ar" : "en";
}

function welcomeTextForProject(project) {
  if (!project || !project.welcome) {
    const lang = uiLanguage();
    return DEFAULT_WELCOME[lang] || DEFAULT_WELCOME.en;
  }
  const lang = uiLanguage();
  return project.welcome[lang] || project.welcome.en || project.welcome.ar || DEFAULT_WELCOME[lang];
}

function hasUserMessages() {
  return el.chatLog.querySelectorAll(".message.user").length > 0;
}

function setWelcomeMessage(text) {
  const bubble = document.getElementById("welcomeMessage");
  if (!bubble) return;
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
}

function refreshWelcomeMessage() {
  const project = state.projects.find((p) => p.id === state.activeProjectId);
  if (!hasUserMessages()) {
    setWelcomeMessage(welcomeTextForProject(project));
  }
}

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
  skillPicker: $("skillPicker"),
  skillHint: $("skillHint"),
  
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
  refreshWelcomeMessage();
  refreshSkillPicker();
}

function getActiveProject() {
  return state.projects.find(x => x.id === state.activeProjectId) || null;
}

function getActiveProjectNumericId() {
  const p = getActiveProject();
  return p ? p.project_id : null;
}

function refreshSkillPicker() {
  const project = getActiveProject();
  state.skills = (project && Array.isArray(project.skills)) ? project.skills : [];
  const picker = el.skillPicker;
  const hint = el.skillHint;
  if (!picker) return;

  if (!state.skills.length) {
    picker.style.display = "none";
    if (hint) hint.style.display = "none";
    state.selectedSkillId = "";
    localStorage.removeItem("algorag.selectedSkillId");
    return;
  }

  picker.style.display = "flex";
  if (hint) hint.style.display = "block";
  picker.innerHTML = "";

  const known = state.skills.some((s) => s.id === state.selectedSkillId);
  if (!known) {
    state.selectedSkillId = "";
    localStorage.removeItem("algorag.selectedSkillId");
  }

  state.skills.forEach((skill) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "skill-btn";
    btn.textContent = skill.name || skill.id;
    btn.title = skill.description || skill.id;
    btn.style.cssText = "padding: 0.35rem 0.75rem; border-radius: 999px; border: 1px solid var(--border-color); background: var(--bg-surface); color: var(--text); cursor: pointer; font-size: 0.8rem;";
    if (skill.id === state.selectedSkillId) {
      btn.style.borderColor = "var(--primary)";
      btn.style.background = "rgba(59,130,246,0.15)";
    }
    btn.addEventListener("click", () => {
      state.selectedSkillId = skill.id;
      localStorage.setItem("algorag.selectedSkillId", skill.id);
      refreshSkillPicker();
      updateSendGate();
    });
    picker.appendChild(btn);
  });
  updateSendGate();
}

function updateSendGate() {
  const needsSkill = state.skills.length > 0;
  const skillOk = !needsSkill || !!state.selectedSkillId;
  const canSend = state.isIndexed && skillOk;
  if (el.questionInput) el.questionInput.disabled = !canSend;
  if (el.sendBtn) el.sendBtn.disabled = !canSend;
  if (el.skillHint) {
    el.skillHint.style.display = needsSkill && !state.selectedSkillId ? "block" : "none";
  }
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
    } else {
      state.isIndexed = false;
      setStatus("warning", "Not Ready", "No documents indexed. Upload files in the Admin Dashboard.");
    }
    refreshSkillPicker();
    updateSendGate();
  } catch (err) {
    state.isIndexed = false;
    setStatus("error", "Error", "Failed to check project status.");
    updateSendGate();
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

  if (state.skills.length > 0 && !state.selectedSkillId) {
    addMessage("assistant", "Select a Skill before asking.");
    return;
  }

  addMessage("user", text);
  el.questionInput.value = "";
  el.questionInput.disabled = true;
  el.sendBtn.disabled = true;
  
  showTyping();

  try {
    const body = {
      text,
      limit: 12,
      session_id: state.sessionId,
    };
    if (state.selectedSkillId) {
      body.skill_id = state.selectedSkillId;
    }
    const payload = await api(`/api/v1/nlp/index/answer/${pId}`, {
      method: "POST",
      body: JSON.stringify(body),
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
  state.sessionId = crypto.randomUUID();
  localStorage.setItem("algorag.sessionId", state.sessionId);
  state.selectedSkillId = "";
  localStorage.removeItem("algorag.selectedSkillId");
  el.chatLog.innerHTML = `
    <div class="message assistant welcome-message">
      <div class="avatar"><span class="material-symbols-outlined">smart_toy</span></div>
      <div class="message-bubble" id="welcomeMessage"></div>
    </div>`;
  refreshWelcomeMessage();
  refreshSkillPicker();
  checkIndexStatus();
});

// Init
el.userId.value = state.userId;
loadProjects();
