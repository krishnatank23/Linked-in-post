const state = {
  userId: null,
  user: null,
};

const fontModes = [
  { label: "Default", className: "" },
  { label: "Editorial", className: "font-demo-editorial" },
  { label: "Pop", className: "font-demo-pop" },
];

const demoUser = {
  fullName: "Demo Creator",
  email: "demo.branding@example.com",
  password: "DemoPass123",
};

const companionTips = [
  "Tip: Start with Run Full Analysis to instantly get your first influencer list.",
  "Tip: Use View Influencers after analysis to inspect ranking scores quickly.",
  "Tip: Generate Strategy before Generate Post for stronger content prompts.",
  "Tip: Use Shuffle Theme and Font Demo to personalize your workspace mood.",
];
let companionTipIndex = 0;

// Removed: apiBaseEl, outputEl, fontDemoToggleEl (UI elements no longer displayed)
let fontModeIndex = Number(localStorage.getItem("fontModeIndex") || 0);

if (!Number.isInteger(fontModeIndex) || fontModeIndex < 0 || fontModeIndex >= fontModes.length) {
  fontModeIndex = 0;
}

// ============ SCROLL ANIMATION UTILITIES ============

function initScrollAnimations() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.animationPlayState = "running";
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll(".scroll-reveal, .scroll-reveal-left, .scroll-reveal-right").forEach((el) => {
    el.style.animationPlayState = "paused";
    observer.observe(el);
  });
}

// ============ LOADING & PROGRESS UTILITIES ============

function createLoadingSpinner() {
  const spinner = document.createElement("div");
  spinner.className = "loading-spinner";
  return spinner;
}

function showLoadingState(buttonEl, text = "Loading...") {
  if (!buttonEl) return;
  buttonEl.disabled = true;
  const originalHTML = buttonEl.innerHTML;
  const spinner = createLoadingSpinner();
  buttonEl.innerHTML = "";
  buttonEl.appendChild(spinner);
  buttonEl.appendChild(document.createTextNode(` ${text}`));
  return () => {
    buttonEl.innerHTML = originalHTML;
    buttonEl.disabled = false;
  };
}

function showProgressBar(containerId, duration = 3000) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let progressDiv = container.querySelector(".progress-bar");
  if (!progressDiv) {
    progressDiv = document.createElement("div");
    progressDiv.className = "progress-bar";
    const fillDiv = document.createElement("div");
    fillDiv.className = "progress-bar-fill";
    progressDiv.appendChild(fillDiv);
    container.insertBefore(progressDiv, container.firstChild);
  }

  const fillDiv = progressDiv.querySelector(".progress-bar-fill");
  fillDiv.style.width = "0%";
  fillDiv.style.animation = "none";
  
  // Trigger reflow
  void fillDiv.offsetWidth;
  
  fillDiv.style.transition = `width ${duration}ms ease-out`;
  fillDiv.style.width = "100%";

  setTimeout(() => {
    fillDiv.style.opacity = "0";
    fillDiv.style.transition = "opacity 400ms ease-out";
    setTimeout(() => {
      progressDiv.remove();
    }, 400);
  }, duration + 200);
}

// ============ PAGE TRANSITION UTILITIES ============

function showPage(pageId) {
  const allPages = document.querySelectorAll(".page");
  const targetPage = document.getElementById(pageId);

  allPages.forEach((p) => {
    if (p.id !== pageId) {
      p.classList.remove("active");
      p.style.animation = "fadeOutDown 300ms ease-in forwards";
    }
  });

  if (targetPage) {
    targetPage.classList.add("active");
    targetPage.style.animation = "fadeInUp 400ms ease-out forwards";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// ============ FEEDBACK UTILITIES ============

function showStatusMessage(elementId, message, type = "info", duration = 4000) {
  const statusEl = document.getElementById(elementId);
  if (!statusEl) return;

  statusEl.textContent = message;
  statusEl.classList.remove("error", "success", "warning");
  if (type) statusEl.classList.add(type);
  statusEl.style.animation = "slideInLeft 400ms ease-out";

  if (duration > 0) {
    setTimeout(() => {
      statusEl.style.animation = "slideInLeft 300ms ease-out reverse";
      setTimeout(() => {
        statusEl.textContent = "";
        statusEl.className = "status";
      }, 300);
    }, duration);
  }
}

// ============ STAT ANIMATION UTILITIES ============

function animateCounter(element, targetValue, duration = 1000) {
  if (!element || typeof targetValue !== "number") return;

  const startValue = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const current = Math.floor(startValue + (targetValue - startValue) * progress);

    element.textContent = current;

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

// ============ INTERACTIVE BUTTON EFFECTS ============

function addRippleEffect(button, event) {
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  ripple.style.left = `${event.offsetX}px`;
  ripple.style.top = `${event.offsetY}px`;
  button.appendChild(ripple);
  setTimeout(() => ripple.remove(), 560);
}

// ============ FONT MODE ============

function applyFontMode(index) {
  const body = document.body;
  fontModes.forEach((mode) => {
    if (mode.className) {
      body.classList.remove(mode.className);
    }
  });

  const selected = fontModes[index] || fontModes[0];
  if (selected.className) {
    body.classList.add(selected.className);
  }

  localStorage.setItem("fontModeIndex", String(index));
}

function apiBase() {
  return "http://127.0.0.1:8000";
}

function print(label, data) {
  // Logging disabled: response console removed from UI
  console.log(`[${label}]`, data);
}

function setAuth(user) {
  state.user = user;
  state.userId = user?.user_id ?? null;
  const greetingEl = document.getElementById("userGreeting");
  if (greetingEl) {
    const newText = state.userId ? `Welcome, ${user.full_name}` : "Welcome!";
    greetingEl.style.animation = "slideInLeft 400ms ease-out";
    greetingEl.textContent = newText;
  }
}

function setCompanionText(text) {
  const el = document.getElementById("aiCompanionText");
  if (el) {
    el.style.animation = "fadeInUp 300ms ease-out";
    el.textContent = text;
  }
}

function ensureAuth() {
  if (!state.userId) {
    throw new Error("Please login or register first.");
  }
}

function getSelectedWeekdays() {
  return Array.from(document.querySelectorAll(".weekday-picker input[type='checkbox']:checked"))
    .map((el) => Number(el.value))
    .filter((day) => Number.isInteger(day) && day >= 0 && day <= 6);
}

function prefillTimezone() {
  const tzEl = document.getElementById("notifTimezone");
  if (!tzEl) return;
  const detected = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const hasOption = Array.from(tzEl.options).some((opt) => opt.value === detected);
  if (hasOption) {
    tzEl.value = detected;
  }
}

function formatApiDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const path = Array.isArray(item.loc) ? item.loc.join(".") : "field";
          const msg = item.msg || JSON.stringify(item);
          return `${path}: ${msg}`;
        }
        return String(item);
      })
      .join(" | ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return String(detail || "Unknown error");
}

async function postJson(path, payload) {
  const response = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = formatApiDetail(body.detail);
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return body;
}

async function fetchProfileStatus() {
  ensureAuth();
  const response = await fetch(`${apiBase()}/profile-status?user_id=${encodeURIComponent(state.userId)}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `Profile status failed: ${response.status}`);
  }
  return body;
}

async function uploadProfileForCurrentUser(file) {
  ensureAuth();
  if (!file) {
    throw new Error("Please select a profile file first.");
  }

  const uploadForm = new FormData();
  uploadForm.append("user_id", String(state.userId));
  uploadForm.append("profile_file", file);

  const uploadResponse = await fetch(`${apiBase()}/upload-profile`, {
    method: "POST",
    body: uploadForm,
  });

  const uploadBody = await uploadResponse.json().catch(() => ({}));
  if (!uploadResponse.ok) {
    throw new Error(uploadBody.detail || `Upload failed: ${uploadResponse.status}`);
  }

  return uploadBody;
}

function buildNotificationPayload() {
  const weekdays = getSelectedWeekdays();
  if (!weekdays.length) {
    throw new Error("Please select at least one preferred day.");
  }

  const hourRaw = Number(document.getElementById("notifHour").value || 9);
  const preferredHour = Math.min(23, Math.max(0, Number.isFinite(hourRaw) ? hourRaw : 9));
  document.getElementById("notifHour").value = String(preferredHour);

  const cadenceRaw = Number(document.getElementById("notifCadence").value || 3);
  const cadenceDays = Math.min(14, Math.max(1, Number.isFinite(cadenceRaw) ? cadenceRaw : 3));
  document.getElementById("notifCadence").value = String(cadenceDays);

  return {
    user_id: state.userId,
    outlook_email: document.getElementById("notifEmail").value.trim(),
    enabled: document.getElementById("notifEnabled").checked,
    cadence_days: cadenceDays,
    preferred_hour: preferredHour,
    timezone: document.getElementById("notifTimezone").value,
    preferred_weekdays: weekdays,
  };
}

async function saveNotificationSettings() {
  ensureAuth();
  const payload = buildNotificationPayload();
  const result = await postJson("/notification-settings", payload);
  showStatusMessage("notifStatus", "✓ Notification settings saved.", "success", 3000);
  print("Notification settings", result);
  return result;
}

function applyGeneratedTheme() {
  const palettes = [
    { hue: 206, accent: 52, glow: 198, bg: 206 },
    { hue: 214, accent: 48, glow: 190, bg: 210 },
    { hue: 220, accent: 56, glow: 202, bg: 214 },
    { hue: 200, accent: 44, glow: 186, bg: 202 },
  ];
  const theme = palettes[Math.floor(Math.random() * palettes.length)];

  const root = document.documentElement;
  root.style.setProperty("--bg", `hsl(${theme.bg} 100% 98%)`);
  root.style.setProperty("--text", `hsl(${theme.hue} 42% 16%)`);
  root.style.setProperty("--muted", `hsl(${theme.hue} 20% 38%)`);
  root.style.setProperty("--primary", `hsl(${theme.hue} 86% 62%)`);
  root.style.setProperty("--accent", `hsl(${theme.accent} 96% 68%)`);
  root.style.setProperty("--glow", `hsl(${theme.glow} 88% 82%)`);
  root.style.setProperty("--surface", "hsl(0 0% 100% / 0.82)");
  root.style.setProperty("--surface-border", `hsl(${theme.hue} 42% 46% / 0.18)`);
}

// ============ PAGE NAVIGATION AND BUTTONS ============

document.getElementById("startLogin").addEventListener("click", () => showPage("loginPage"));
document.getElementById("startRegister").addEventListener("click", () => showPage("registerPage"));

// Back Buttons
document.getElementById("backFromLogin").addEventListener("click", () => showPage("welcomePage"));
document.getElementById("backFromRegister").addEventListener("click", () => showPage("welcomePage"));

document.getElementById("fillLoginDemo").addEventListener("click", () => {
  const form = document.getElementById("loginForm");
  form.elements.email.value = demoUser.email;
  form.elements.password.value = demoUser.password;
  showStatusMessage("loginStatus", "✓ Demo login details filled.", "success", 2000);
});

document.getElementById("fillRegisterDemo").addEventListener("click", () => {
  const form = document.getElementById("registerForm");
  form.elements.full_name.value = demoUser.fullName;
  form.elements.email.value = demoUser.email;
  form.elements.password.value = demoUser.password;
  form.elements.password_confirm.value = demoUser.password;
  showStatusMessage("registerStatus", "✓ Demo details filled. Choose a profile file to continue.", "success", 2000);
});

// Logout
document.getElementById("logout").addEventListener("click", () => {
  state.userId = null;
  state.user = null;
  showPage("welcomePage");
  showStatusMessage("loginStatus", "", "info", 0);
  setCompanionText(companionTips[0]);
});

// ============ FORM SUBMISSIONS ============

document.getElementById("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const formData = new FormData(event.target);
    const resetSpinner = showLoadingState(event.submitter);
    const payload = {
      email: String(formData.get("email") || "").trim(),
      password: String(formData.get("password") || "").trim(),
    };

    if (!payload.password) {
      throw new Error("Password is required.");
    }

    const result = await postJson("/login", payload);
    setAuth(result);
    print("Login successful", result);

    try {
      const profileStatus = await fetchProfileStatus();
      if (!profileStatus.has_profile) {
        setCompanionText("No saved profile found for this account. Please upload in Profile Upload, then run analysis.");
        showStatusMessage("dashboardUploadStatus", "No profile found. Please upload your profile file below.", "warning", 5000);
      }
    } catch (statusError) {
      print("Profile status check error", String(statusError.message || statusError));
    }

    showStatusMessage("loginStatus", "✓ Login successful! Redirecting...", "success", 1500);
    
    setTimeout(() => {
      showPage("dashboardPage");
      document.getElementById("loginForm").reset();
    }, 1500);
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    showStatusMessage("loginStatus", `✗ ${error.message || error}`, "error", 4000);
    print("Login error", String(error.message || error));
    if (event.submitter) event.submitter.disabled = false;
  }
});

document.getElementById("registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const formData = new FormData(event.target);
    const resetSpinner = showLoadingState(event.submitter);

    const password = String(formData.get("password") || "").trim();
    const passwordConfirm = String(formData.get("password_confirm") || "").trim();

    if (password !== passwordConfirm) {
      throw new Error("Passwords do not match.");
    }

    if (!password || password.length < 6) {
      throw new Error("Password must be at least 6 characters.");
    }

    const fileInput = document.getElementById("profileFileReg");
    if (!fileInput.files?.length) {
      throw new Error("Profile file is required.");
    }

    // Step 1: Register user
    const registerPayload = {
      email: String(formData.get("email") || "").trim(),
      full_name: String(formData.get("full_name") || "").trim(),
      password: password,
    };

    const registerResult = await postJson("/register", registerPayload);
    setAuth(registerResult);
    print("Registration successful", registerResult);
    showProgressBar("registerStatus", 2000);

    // Step 2: Upload profile
    const uploadBody = await uploadProfileForCurrentUser(fileInput.files[0]);

    print("Profile uploaded successfully", uploadBody);
    showStatusMessage("registerStatus", "✓ Account created and profile uploaded! Redirecting...", "success", 1500);
    
    setTimeout(() => {
      showPage("dashboardPage");
      document.getElementById("registerForm").reset();
    }, 1500);
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    const msg = String(error.message || error);
    if (msg.toLowerCase().includes("upload")) {
      showStatusMessage(
        "registerStatus",
        `✗ ${msg}. Account may be created, but profile was not saved. Login and use Profile Upload in dashboard.`,
        "error",
        7000
      );
    } else {
      showStatusMessage("registerStatus", `✗ ${msg}`, "error", 4000);
    }
    print("Registration error", String(error.message || error));
    if (event.submitter) event.submitter.disabled = false;
  }
});

document.getElementById("dashboardUploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    ensureAuth();
    const resetSpinner = showLoadingState(event.submitter, "Uploading...");
    const fileInput = document.getElementById("dashboardProfileFile");
    const file = fileInput?.files?.[0];
    const result = await uploadProfileForCurrentUser(file);

    showStatusMessage("dashboardUploadStatus", "✓ Profile uploaded successfully. You can run analysis now.", "success", 5000);
    setCompanionText("Profile saved successfully. Run Full Analysis now.");
    print("Dashboard profile upload successful", result);
    event.target.reset();
    if (resetSpinner) resetSpinner();
  } catch (error) {
    showStatusMessage("dashboardUploadStatus", `✗ ${error.message || error}`, "error", 5000);
    print("Dashboard profile upload error", String(error.message || error));
  }
});

// ============ DASHBOARD CONTROLS ============

document.getElementById("runAnalysisBtn").addEventListener("click", async (event) => {
  try {
    ensureAuth();
    const resetSpinner = showLoadingState(event.target, "Analyzing...");
    showProgressBar("workflow-card", 4000);
    print("Starting analysis...", "Processing...");
    
    const result = await postJson("/run-analysis", { user_id: state.userId });
    print("Analysis completed", result);

    // Automatically load influencers after analysis
    const influencers = await fetch(`${apiBase()}/influencers?user_id=${encodeURIComponent(state.userId)}`).then((r) =>
      r.json()
    );
    displayInfluencers(influencers);
    setCompanionText("✓ Analysis complete! Check out your top influencers below.");
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    print("Analysis error", String(error.message || error));
    const msg = String(error.message || error);
    if (msg.toLowerCase().includes("profile not found")) {
      setCompanionText("Profile not found for this account. Upload it in the Profile Upload section, then run analysis again.");
      showStatusMessage("dashboardUploadStatus", "Please upload your profile file here, then run analysis again.", "warning", 6000);
      const uploadCard = document.getElementById("profileUploadCard");
      if (uploadCard) {
        uploadCard.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else {
      setCompanionText(`Error during analysis: ${msg}`);
    }
  }
});

document.getElementById("loadInfluencersBtn").addEventListener("click", async (event) => {
  try {
    ensureAuth();
    const resetSpinner = showLoadingState(event.target, "Loading...");
    
    const response = await fetch(`${apiBase()}/influencers?user_id=${encodeURIComponent(state.userId)}`);
    const influencers = await response.json().catch(() => []);
    if (!response.ok) {
      throw new Error(influencers.detail || `Fetch failed: ${response.status}`);
    }
    displayInfluencers(influencers);
    print("Influencers loaded", influencers);
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    print("Influencer load error", String(error.message || error));
  }
});

document.getElementById("loadGapAnalysisBtn").addEventListener("click", async (event) => {
  try {
    ensureAuth();
    const resetSpinner = showLoadingState(event.target, "Analyzing...");
    
    const response = await fetch(`${apiBase()}/gap-analysis?user_id=${encodeURIComponent(state.userId)}`);
    const gaps = await response.json().catch(() => []);
    if (!response.ok) {
      throw new Error(gaps.detail || `Fetch failed: ${response.status}`);
    }
    print("Gap Analysis", gaps);
    setCompanionText(`Found ${gaps.length || 0} gaps in your content strategy.`);
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    print("Gap analysis error", String(error.message || error));
  }
});

document.getElementById("generateStrategyBtn").addEventListener("click", async (event) => {
  try {
    ensureAuth();
    const resetSpinner = showLoadingState(event.target, "Generating...");
    showProgressBar("workflow-card", 3000);
    
    const result = await postJson("/generate-strategy", { user_id: state.userId });
    print("Generated strategy", result);
    setCompanionText("✓ Strategy generated! Review the insights and plan your next moves.");
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    print("Strategy error", String(error.message || error));
  }
});

document.getElementById("postForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    ensureAuth();
    const resetSpinner = showLoadingState(event.submitter, "Generating...");
    showProgressBar("post-card", 3000);
    
    const topic = document.getElementById("postTopic").value.trim();
    const objective = document.getElementById("postObjective").value.trim();
    const mediaContext = document.getElementById("mediaContext").value.trim();

    if (!topic) {
      throw new Error("Topic is required.");
    }

    const result = await postJson("/generate-post", {
      user_id: state.userId,
      topic,
      objective: objective || "engagement",
      media_context: mediaContext || null,
    });
    print("Generated post", result);
    showStatusMessage("post-card", "✓ Post generated successfully!", "success", 3000);
    
    if (resetSpinner) resetSpinner();
  } catch (error) {
    print("Post generation error", String(error.message || error));
    setCompanionText(`Post generation issue: ${error.message}`);
  }
});

document.getElementById("notificationForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const resetSpinner = showLoadingState(event.submitter, "Saving...");
    await saveNotificationSettings();
    if (resetSpinner) resetSpinner();
  } catch (error) {
    showStatusMessage("notifStatus", `✗ ${error.message || error}`, "error", 4000);
    print("Notification settings error", String(error.message || error));
  }
});

document.getElementById("sendNotifBtn").addEventListener("click", async (event) => {
  try {
    const resetSpinner = showLoadingState(event.target, "Sending...");
    await saveNotificationSettings();
    const result = await postJson("/send-post-notification", { user_id: state.userId, force_send: true });
    showStatusMessage("notifStatus", "✓ Test notification sent to your inbox!", "success", 4000);
    print("Notification send result", result);
    if (resetSpinner) resetSpinner();
  } catch (error) {
    showStatusMessage("notifStatus", `✗ ${error.message || error}`, "error", 4000);
    print("Notification send error", String(error.message || error));
  }
});

// ============ AI COMPANION CONTROLS ============

const aiTipBtn = document.getElementById("aiTipBtn");
const playfulModeBtn = document.getElementById("playfulModeBtn");
const runGuideBtn = document.getElementById("runGuideBtn");

if (aiTipBtn) {
  aiTipBtn.addEventListener("click", () => {
    companionTipIndex = (companionTipIndex + 1) % companionTips.length;
    setCompanionText(companionTips[companionTipIndex]);
  });
}

if (playfulModeBtn) {
  playfulModeBtn.addEventListener("click", () => {
    document.body.classList.toggle("playful-on");
    const enabled = document.body.classList.contains("playful-on");
    setCompanionText(enabled ? "🎉 Playful mode is ON. Enjoy the extra motion vibes!" : companionTips[0]);
  });
}

if (runGuideBtn) {
  runGuideBtn.addEventListener("click", () => {
    if (!state.userId) {
      showPage("registerPage");
      setCompanionText("Let us begin: create your account and upload your profile first.");
      return;
    }

    document.getElementById("runAnalysisBtn").click();
    setCompanionText("🚀 Running analysis now. Next step: review your influencer list.");
  });
}

// ============ BUTTON EFFECTS ============

document.querySelectorAll(".btn").forEach((button) => {
  button.addEventListener("click", (event) => {
    // Only add ripple if not a disabled button
    if (!button.disabled) {
      addRippleEffect(button, event);
    }
  });
});

// ============ INFLUENCER DISPLAY ============

function displayInfluencers(influencers) {
  const list = document.getElementById("influencersList");
  if (!influencers || influencers.length === 0) {
    list.innerHTML = '<p class="empty-state">No influencers found. Run analysis first.</p>';
    return;
  }

  list.innerHTML = influencers
    .map(
      (inf, idx) => `
    <div class="influencer-item" style="animation-delay: ${idx * 50}ms;">
      <div class="influencer-info">
        <div class="influencer-content">
          <h4>${inf.name}</h4>
          <span class="influencer-score">Score: ${inf.rank_score}</span>
        </div>
        <p>${inf.description}</p>
        <a href="${inf.profile_link}" target="_blank" style="color: var(--primary); text-decoration: none; font-size: 0.9rem; font-weight: 600;">
          View Profile →
        </a>
      </div>
    </div>
  `
    )
    .join("");

  // Add scroll-reveal animation to each item
  list.querySelectorAll(".influencer-item").forEach((item) => {
    item.classList.add("scroll-reveal");
  });
}

// ============ INITIALIZATION ============

applyGeneratedTheme();
applyFontMode(fontModeIndex);
setCompanionText(companionTips[0]);
prefillTimezone();

// Initialize scroll animations after page load
window.addEventListener("load", () => {
  initScrollAnimations();
  
  // Add scroll-reveal class to cards for staggered animation
  document.querySelectorAll(".card").forEach((card, idx) => {
    if (!card.classList.contains("scroll-reveal") && !card.classList.contains("scroll-reveal-left")) {
      card.classList.add(idx % 2 === 0 ? "scroll-reveal-left" : "scroll-reveal-right");
    }
  });
});

// Smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  });
});
