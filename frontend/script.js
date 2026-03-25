const state = {
  user: null,
  userId: null,
};

function byId(id) {
  return document.getElementById(id);
}

function apiBase() {
  return "http://127.0.0.1:8000";
}

function setStatus(id, message, level = "") {
  const el = byId(id);
  el.textContent = message || "";
  el.className = "status";
  if (level) el.classList.add(level);
}

function setOutput(payload) {
  const text = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  byId("outputBox").textContent = text;
}

function toggleAuthTab(tab) {
  const isRegister = tab === "register";
  byId("showRegisterBtn").classList.toggle("active", isRegister);
  byId("showLoginBtn").classList.toggle("active", !isRegister);
  byId("registerForm").classList.toggle("active", isRegister);
  byId("loginForm").classList.toggle("active", !isRegister);
}

function setDashboard(visible) {
  byId("authView").classList.toggle("active", !visible);
  byId("dashboardView").classList.toggle("active", visible);
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(body));
  }
  return body;
}

async function postJson(path, payload) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function postForm(path, formData) {
  return request(path, {
    method: "POST",
    body: formData,
  });
}

function setLoading(btn, text) {
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = text;
  return () => {
    btn.disabled = false;
    btn.textContent = original;
  };
}

function wirePasswordToggles() {
  document.querySelectorAll(".toggle-pass[data-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const input = targetId ? byId(targetId) : null;
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.textContent = showing ? "Show" : "Hide";
    });
  });
}

function renderProfileMeta(profileStatus, profileOverview) {
  const meta = [
    ["Email", state.user?.email || "-"],
    ["Full Name", state.user?.full_name || "-"],
    ["User ID", String(state.userId || "-")],
    ["Has Profile", profileStatus?.has_profile ? "Yes" : "No"],
    ["Profile ID", profileStatus?.profile_id ? String(profileStatus.profile_id) : "-"],
    ["Source", profileStatus?.source_type || "-"],
    ["Industry", profileOverview?.profile?.industry || "-"],
    ["Skills Count", String(profileOverview?.profile?.skills_count || 0)],
  ];

  byId("profileMeta").innerHTML = meta
    .map(([k, v]) => `<div><strong>${k}</strong></div><div>${v}</div>`)
    .join("");
}

async function refreshDashboard() {
  if (!state.userId) return;
  const [profileStatus, overview] = await Promise.all([
    request(`/profile-status?user_id=${encodeURIComponent(state.userId)}`),
    request(`/pipeline/overview?user_id=${encodeURIComponent(state.userId)}`),
  ]);

  renderProfileMeta(profileStatus, overview);
  if (profileStatus.has_profile) {
    setStatus("profileStatus", "Resume profile loaded from database successfully.", "ok");
  } else {
    setStatus("profileStatus", "No resume profile found for this account.", "warn");
  }

  setOutput({ profileStatus, overview });
}

byId("showRegisterBtn").addEventListener("click", () => toggleAuthTab("register"));
byId("showLoginBtn").addEventListener("click", () => toggleAuthTab("login"));

byId("registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = byId("registerBtn");
  const reset = setLoading(btn, "Creating account...");

  try {
    const form = new FormData(event.target);
    const pass = String(form.get("password") || "");
    const confirm = String(form.get("password_confirm") || "");
    if (pass !== confirm) {
      throw new Error("Passwords do not match.");
    }

    const file = byId("registerProfileFile").files?.[0];
    if (!file) {
      throw new Error("Please upload resume/LinkedIn file.");
    }

    const payload = new FormData();
    payload.append("full_name", String(form.get("full_name") || "").trim());
    payload.append("email", String(form.get("email") || "").trim());
    payload.append("password", pass);
    payload.append("profile_file", file);

    const result = await postForm("/register", payload);
    setStatus("authStatus", "Registration successful. Your resume is saved in database. Login now.", "ok");
    setOutput(result);
    toggleAuthTab("login");
  } catch (error) {
    setStatus("authStatus", String(error.message || error), "error");
  } finally {
    reset();
  }
});

byId("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = byId("loginBtn");
  const reset = setLoading(btn, "Signing in...");

  try {
    const form = new FormData(event.target);
    const payload = {
      email: String(form.get("email") || "").trim(),
      password: String(form.get("password") || ""),
    };

    const result = await postJson("/login", payload);
    state.user = result;
    state.userId = result.user_id;

    byId("welcomeText").textContent = `Welcome, ${result.full_name}`;
    setDashboard(true);
    await refreshDashboard();
    setStatus("authStatus", "", "");
  } catch (error) {
    setStatus("authStatus", String(error.message || error), "error");
  } finally {
    reset();
  }
});

byId("refreshBtn").addEventListener("click", async () => {
  try {
    await refreshDashboard();
  } catch (error) {
    setOutput(String(error.message || error));
  }
});

byId("logoutBtn").addEventListener("click", () => {
  state.user = null;
  state.userId = null;
  setDashboard(false);
  setStatus("authStatus", "Logged out.");
  setOutput("Session cleared.");
});

byId("runPipelineBtn").addEventListener("click", async (event) => {
  const reset = setLoading(event.target, "Running...");
  try {
    const result = await postJson("/pipeline/full-run", { user_id: state.userId });
    setOutput(result);
    await refreshDashboard();
  } catch (error) {
    setOutput(String(error.message || error));
  } finally {
    reset();
  }
});

byId("loadInfluencersBtn").addEventListener("click", async (event) => {
  const reset = setLoading(event.target, "Loading...");
  try {
    const result = await request(`/influencers?user_id=${encodeURIComponent(state.userId)}`);
    setOutput(result);
  } catch (error) {
    setOutput(String(error.message || error));
  } finally {
    reset();
  }
});

byId("genStrategyBtn").addEventListener("click", async (event) => {
  const reset = setLoading(event.target, "Generating...");
  try {
    const result = await postJson("/generate-strategy", { user_id: state.userId });
    setOutput(result);
  } catch (error) {
    setOutput(String(error.message || error));
  } finally {
    reset();
  }
});

byId("genPostBtn").addEventListener("click", async (event) => {
  const reset = setLoading(event.target, "Generating...");
  try {
    const topic = String(byId("postTopic").value || "").trim() || "LinkedIn growth";
    const result = await postJson("/generate-post", {
      user_id: state.userId,
      topic,
      objective: "engagement",
    });
    setOutput(result);
  } catch (error) {
    setOutput(String(error.message || error));
  } finally {
    reset();
  }
});

setDashboard(false);
toggleAuthTab("register");
wirePasswordToggles();
setOutput("Ready. Register with resume to begin.");
