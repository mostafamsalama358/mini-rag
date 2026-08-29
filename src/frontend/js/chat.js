const state = {
  userId: localStorage.getItem("algorag.userId") || "demo-user",
  projects: [],
  activeProjectId: localStorage.getItem("algorag.activeProjectId") || "",
  sessionId: localStorage.getItem("algorag.sessionId") || crypto.randomUUID(),
  isIndexed: false,
  selectedSkillId: localStorage.getItem("algorag.selectedSkillId") || "",
  selectedSubject: localStorage.getItem("algorag.selectedSubject") || "",
  skills: [],
  uploading: false,
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
  attachBtn: $("attachBtn"),
  chatFileInput: $("chatFileInput"),
  attachHint: $("attachHint"),
  skillPicker: $("skillPicker"),
  skillHint: $("skillHint"),
  
  // Status banner
  projectStatusBanner: $("projectStatusBanner"),
  statusIcon: $("statusIcon"),
  statusTitle: $("statusTitle"),
  statusDetail: $("statusDetail")
};

const CHAT_UPLOAD_EXT = /\.(xlsx|xls|csv)$/i;

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

function projectAllowsChatUpload() {
  const p = getActiveProject();
  if (!p) return false;
  if ((p.name || "").trim().toLowerCase() === "grc") return true;
  return (p.skills || []).some((s) => s.id === "financial_audit");
}

function refreshAttachControl() {
  const allow = projectAllowsChatUpload();
  if (el.attachBtn) {
    el.attachBtn.style.display = allow ? "flex" : "none";
    el.attachBtn.disabled = !allow || !getActiveProjectNumericId() || state.uploading;
  }
  if (el.attachHint) {
    el.attachHint.style.display = allow ? "block" : "none";
  }
  if (el.questionInput) {
    el.questionInput.classList.toggle("has-attach", allow);
  }
}

function isGroupedSkillCatalog(skills) {
  return skills.length > 0 && skills.every((s) => typeof s.subject === "string" && s.subject);
}

function uniqueSubjects(skills) {
  const seen = [];
  const labels = {};
  skills.forEach((skill) => {
    if (!skill.subject || labels[skill.subject]) return;
    labels[skill.subject] = skill.subject_label || skill.subject;
    seen.push(skill.subject);
  });
  return seen.map((id) => ({ id, label: labels[id] }));
}

function skillHintCopy() {
  const ar = uiLanguage() === "ar";
  if (isGroupedSkillCatalog(state.skills)) {
    if (!state.selectedSubject) {
      return ar ? "اختر المادة أولاً." : "Select a subject first.";
    }
    if (!state.selectedSkillId) {
      return ar ? "اختر نوع السؤال (شرح، ملخص، تمرين، …)." : "Select what you need (Explain, Summary, Exercise, …).";
    }
    return "";
  }
  return ar ? "اختر مهارة قبل السؤال." : "Select a Skill before asking.";
}

function makeChip({ className, label, title, selected, onClick }) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = className + (selected ? " is-selected" : "");
  btn.textContent = label;
  btn.title = title || label;
  btn.addEventListener("click", onClick);
  return btn;
}

function renderFlatSkillPicker(picker) {
  picker.style.flexDirection = "row";
  state.skills.forEach((skill) => {
    picker.appendChild(makeChip({
      className: "skill-btn",
      label: skill.name || skill.id,
      title: skill.description || skill.id,
      selected: skill.id === state.selectedSkillId,
      onClick: () => {
        state.selectedSkillId = skill.id;
        localStorage.setItem("algorag.selectedSkillId", skill.id);
        refreshSkillPicker();
        updateSendGate();
      },
    }));
  });
}

function renderGroupedSkillPicker(picker) {
  picker.style.flexDirection = "column";
  const subjects = uniqueSubjects(state.skills);
  const bound = state.skills.find((s) => s.id === state.selectedSkillId);
  if (bound && bound.subject) {
    state.selectedSubject = bound.subject;
    localStorage.setItem("algorag.selectedSubject", state.selectedSubject);
  }
  if (state.selectedSubject && !subjects.some((s) => s.id === state.selectedSubject)) {
    state.selectedSubject = "";
    localStorage.removeItem("algorag.selectedSubject");
  }

  const subjectRow = document.createElement("div");
  subjectRow.className = "skill-picker-row";
  subjects.forEach((subject) => {
    subjectRow.appendChild(makeChip({
      className: "skill-subject-btn",
      label: subject.label,
      title: subject.label,
      selected: subject.id === state.selectedSubject,
      onClick: () => {
        if (state.selectedSubject !== subject.id) {
          const current = state.skills.find((s) => s.id === state.selectedSkillId);
          if (!current || current.subject !== subject.id) {
            state.selectedSkillId = "";
            localStorage.removeItem("algorag.selectedSkillId");
          }
        }
        state.selectedSubject = subject.id;
        localStorage.setItem("algorag.selectedSubject", subject.id);
        refreshSkillPicker();
        updateSendGate();
      },
    }));
  });
  picker.appendChild(subjectRow);

  if (!state.selectedSubject) return;

  const intentRow = document.createElement("div");
  intentRow.className = "skill-picker-row";
  state.skills
    .filter((s) => s.subject === state.selectedSubject)
    .forEach((skill) => {
      intentRow.appendChild(makeChip({
        className: "skill-btn",
        label: skill.name || skill.intent || skill.id,
        title: skill.description || skill.id,
        selected: skill.id === state.selectedSkillId,
        onClick: () => {
          state.selectedSkillId = skill.id;
          localStorage.setItem("algorag.selectedSkillId", skill.id);
          refreshSkillPicker();
          updateSendGate();
        },
      }));
    });
  picker.appendChild(intentRow);
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
    state.selectedSubject = "";
    localStorage.removeItem("algorag.selectedSkillId");
    localStorage.removeItem("algorag.selectedSubject");
    updateSendGate();
    return;
  }

  picker.style.display = "flex";
  picker.innerHTML = "";

  const known = state.skills.some((s) => s.id === state.selectedSkillId);
  if (!known) {
    state.selectedSkillId = "";
    localStorage.removeItem("algorag.selectedSkillId");
  }

  if (isGroupedSkillCatalog(state.skills)) {
    renderGroupedSkillPicker(picker);
  } else {
    renderFlatSkillPicker(picker);
  }
  updateSendGate();
}

function updateSendGate() {
  const needsSkill = state.skills.length > 0;
  const skillOk = !needsSkill || !!state.selectedSkillId;
  const canSend = state.isIndexed && skillOk && !state.uploading;
  if (el.questionInput) el.questionInput.disabled = !canSend;
  if (el.sendBtn) el.sendBtn.disabled = !canSend;
  if (el.skillHint) {
    const text = skillHintCopy();
    el.skillHint.textContent = text || (uiLanguage() === "ar" ? "اختر مهارة قبل السؤال." : "Select a Skill before asking.");
    el.skillHint.style.display = needsSkill && !state.selectedSkillId ? "block" : "none";
  }
  refreshAttachControl();
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
      const uploadHint = projectAllowsChatUpload()
        ? " Use the upload icon to add Excel/CSV for audit."
        : "";
      setStatus("success", "Ready", `${records} chunks indexed. You can ask questions.${uploadHint}`);
    } else {
      state.isIndexed = false;
      const notReady = projectAllowsChatUpload()
        ? "No documents indexed. Upload Excel/CSV with the paperclip icon, or use Admin."
        : "No documents indexed. Upload files in the Admin Dashboard.";
      setStatus("warning", "Not Ready", notReady);
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
function addMessage(role, text, { json = false } = {}) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;
  
  const avatarDiv = document.createElement("div");
  avatarDiv.className = "avatar";
  
  const iconSpan = document.createElement("span");
  iconSpan.className = "material-symbols-outlined";
  iconSpan.textContent = role === "user" ? "person" : "smart_toy";
  avatarDiv.appendChild(iconSpan);
  
  const bubbleDiv = document.createElement("div");
  bubbleDiv.className = json ? "message-bubble audit-json" : "message-bubble";
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

const AUTO_AUDIT_QUERY =
  "Audit all uploaded journal transactions for tax, credit, cut-off and fraud violations. Return the JSON audit report only.";

function ruleTax002IsFalsePositive(text) {
  const blob = String(text || "");
  const taxM = blob.match(/tax\s*(?:amount)?\s*(?:\(|:|=)?\s*(-?\d+(?:[.,]\d+)?)/i);
  const untaxM = blob.match(/untaxed\s*(?:amount)?\s*(?:\(|:|=)?\s*(-?\d+(?:[.,]\d+)?)/i);
  if (!taxM || !untaxM) return false;
  const tax = parseFloat(taxM[1].replace(",", ""));
  const untaxed = parseFloat(untaxM[1].replace(",", ""));
  // Only Tax vs Untaxed×0.14 (do not drop real Tax=0 cases that also show expected VAT).
  return Number.isFinite(tax) && Number.isFinite(untaxed) && Math.abs(untaxed * 0.14 - tax) <= 0.05;
}

function sanitizeFinancialAuditJson(payload) {
  if (!payload || typeof payload !== "object" || !Array.isArray(payload.issues)) {
    return payload;
  }
  const cleanMarkers = [
    "this transaction is compliant",
    "transaction is compliant",
    "no corrective action",
    "no action needed",
  ];
  const kept = payload.issues.filter((issue) => {
    if (!issue || typeof issue !== "object") return false;
    const blob = [issue.root_cause, issue.corrective_action, issue.violation_type]
      .map((x) => String(x || ""))
      .join(" ");
    const lower = blob.toLowerCase();
    if (cleanMarkers.some((m) => lower.includes(m))) return false;
    if (String(issue.rule_id || "").toUpperCase() === "RULE-TAX-002" && ruleTax002IsFalsePositive(blob)) {
      return false;
    }
    return true;
  });
  payload.issues = kept;
  if (payload.executive_summary && typeof payload.executive_summary === "object") {
    payload.executive_summary.violations_found = kept.length;
    const dist = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const issue of kept) {
      const level = String(issue.risk_level || "").toLowerCase();
      if (level in dist) dist[level] += 1;
    }
    payload.executive_summary.risk_distribution = dist;
    if (!kept.length) {
      payload.executive_summary.overall_compliance_assessment =
        "No confirmed violations in the reviewed transaction sample (false-positive VAT matches removed).";
    }
  }
  return payload;
}

function formatAnswerText(raw) {
  if (raw == null) return "No answer returned.";
  const text = String(raw).trim();
  if (!text) return "No answer returned.";
  const tryParse = (value) => {
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  };
  let parsed = tryParse(text);
  if (!parsed) {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start >= 0 && end > start) parsed = tryParse(text.slice(start, end + 1));
  }
  if (parsed && typeof parsed === "object") {
    if (state.selectedSkillId === "financial_audit" || parsed.issues) {
      parsed = sanitizeFinancialAuditJson(parsed);
    }
    return JSON.stringify(parsed, null, 2);
  }
  return text;
}

function ensureFinancialAuditSkillSelected() {
  const hasSkill = (state.skills || []).some((s) => s.id === "financial_audit");
  if (!hasSkill) return false;
  if (state.selectedSkillId !== "financial_audit") {
    state.selectedSkillId = "financial_audit";
    localStorage.setItem("algorag.selectedSkillId", "financial_audit");
    refreshSkillPicker();
  }
  return true;
}

async function runAnswer(text, { showUserBubble = true } = {}) {
  const pId = getActiveProjectNumericId();
  if (!pId) return null;

  if (state.skills.length > 0 && !state.selectedSkillId) {
    addMessage("assistant", "Select a Skill before asking.");
    return null;
  }

  if (showUserBubble) {
    addMessage("user", text);
  }

  el.questionInput.disabled = true;
  el.sendBtn.disabled = true;
  showTyping();

  try {
    const body = {
      text,
      limit: state.selectedSkillId === "financial_audit" ? 80 : 12,
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
    const answer = formatAnswerText(payload.answer);
    const looksJson = answer.trimStart().startsWith("{") || answer.trimStart().startsWith("[");
    addMessage("assistant", answer, { json: looksJson });
    return payload;
  } catch (error) {
    hideTyping();
    addMessage(
      "assistant",
      `Error: ${error.message === "rag_no_context" ? "Documents are not indexed yet." : error.message}`
    );
    return null;
  } finally {
    updateSendGate();
    if (!el.questionInput.disabled) {
      el.questionInput.focus();
    }
  }
}

// Ask Question
el.chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = el.questionInput.value.trim();
  if (!text) return;
  el.questionInput.value = "";
  await runAnswer(text, { showUserBubble: true });
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

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollTaskUntilDone(taskId, { timeoutMs = 15 * 60 * 1000, intervalMs = 2000 } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const status = await api(`/api/v1/data/tasks/${taskId}`, { method: "GET" });
    if (status.ready) {
      if (status.successful === false) {
        throw new Error(status.error || "Processing failed");
      }
      return status;
    }
    await sleep(intervalMs);
  }
  throw new Error("Processing timed out. Check Admin / Celery status.");
}

async function handleChatFiles(fileList) {
  const files = Array.from(fileList || []).filter((f) => CHAT_UPLOAD_EXT.test(f.name));
  if (!files.length) {
    addMessage("assistant", "Please choose an Excel (.xlsx/.xls) or CSV file.");
    return;
  }

  const pId = getActiveProjectNumericId();
  if (!pId || !projectAllowsChatUpload()) {
    addMessage("assistant", "Select the GRC project first, then upload.");
    return;
  }

  state.uploading = true;
  updateSendGate();

  const names = files.map((f) => f.name).join(", ");
  addMessage("user", `📎 ${names}`);
  setStatus("warning", "Uploading", `Uploading ${files.length} file(s)...`);

  try {
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      await api(`/api/v1/data/upload/${pId}`, { method: "POST", body: form });
    }

    setStatus("warning", "Processing", "Indexing… then running Financial Audit automatically.");

    const processRes = await api(`/api/v1/data/process-and-push/${pId}`, {
      method: "POST",
      body: JSON.stringify({ do_reset: 0 }),
    });

    if (processRes.task_id) {
      await pollTaskUntilDone(processRes.task_id);
    }

    await checkIndexStatus();

    if (!ensureFinancialAuditSkillSelected()) {
      addMessage("assistant", "Upload indexed, but Financial Audit skill is not available on this project.");
      return;
    }

    state.uploading = false;
    setStatus("warning", "Auditing", "Running Financial Audit on uploaded file…");
    await runAnswer(AUTO_AUDIT_QUERY, { showUserBubble: false });
    setStatus("success", "Audit complete", "Financial Audit finished for the uploaded file.");
  } catch (err) {
    setStatus("error", "Upload failed", err.message || "Unknown error");
    addMessage("assistant", `Upload/process error: ${err.message}`);
  } finally {
    state.uploading = false;
    if (el.chatFileInput) el.chatFileInput.value = "";
    updateSendGate();
  }
}

if (el.attachBtn && el.chatFileInput) {
  el.attachBtn.addEventListener("click", () => {
    if (el.attachBtn.disabled) return;
    el.chatFileInput.click();
  });
  el.chatFileInput.addEventListener("change", () => {
    handleChatFiles(el.chatFileInput.files);
  });
}

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
  state.selectedSubject = "";
  localStorage.removeItem("algorag.selectedSkillId");
  localStorage.removeItem("algorag.selectedSubject");
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
