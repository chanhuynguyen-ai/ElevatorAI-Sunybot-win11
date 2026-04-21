// gui/web/static/js/maint.js
import { dom } from "./dom.js";
import { api } from "./api.js";
import { initDataManager } from "./data_manager.js";

function toast(msg) {
  if (window.SunyUI?.showToast) {
    window.SunyUI.showToast(msg);
  } else {
    console.log(msg);
  }
}

let eventsBound = false;
let currentDataTab = "mysql";
let dataExpanded = false;
let maintChatBusy = false;
let legacyMaintAuthed = false;

function showDash(on) {
  if (dom.maintLogin) dom.maintLogin.style.display = on ? "none" : "block";
  if (dom.maintDash) dom.maintDash.style.display = on ? "block" : "none";
}

function setActiveTabButton(activeTab) {
  dom.dataTabMysql?.classList.toggle("active", activeTab === "mysql");
  dom.dataTabMongo?.classList.toggle("active", activeTab === "mongo");

  dom.dataPanelMysql?.classList.toggle("active", activeTab === "mysql");
  dom.dataPanelMongo?.classList.toggle("active", activeTab === "mongo");
}

function setExpandState(expanded) {
  dataExpanded = expanded;
  dom.maintBottomGrid?.classList.toggle("expanded", expanded);

  if (dom.maintExpandBtn) {
    dom.maintExpandBtn.textContent = expanded ? "Thu nhỏ" : "Phóng to";
  }
}

function setChatState(open) {
  dom.maintChatPanel?.classList.toggle("open", open);
  if (open) {
    dom.maintChatInput?.focus();
  }
}

function appendMaintChat(role, text) {
  if (!dom.maintChatMessages) return;

  const bubble = document.createElement("div");
  bubble.className = `maint-chat-bubble ${role}`;
  bubble.textContent = text;
  dom.maintChatMessages.appendChild(bubble);
  dom.maintChatMessages.scrollTop = dom.maintChatMessages.scrollHeight;
}

function bindMaintEvents() {
  if (eventsBound) return;
  eventsBound = true;

  dom.dataTabMysql?.addEventListener("click", () => switchDataTab("mysql"));
  dom.dataTabMongo?.addEventListener("click", () => switchDataTab("mongo"));

  dom.maintExpandBtn?.addEventListener("click", () => toggleDataExpand());
  dom.maintChatToggle?.addEventListener("click", () => toggleMaintChat(true));
  dom.maintChatClose?.addEventListener("click", () => toggleMaintChat(false));
  dom.maintChatSend?.addEventListener("click", () => sendMaintChat());

  dom.maintChatInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMaintChat();
    }
  });
}

export function initMaint() {
  legacyMaintAuthed = false;
  try {
    localStorage.removeItem("maint_authed");
    localStorage.removeItem("maint_emp_code");
    localStorage.removeItem("maint_profile");
  } catch {}
  showDash(false);
  switchDataTab(currentDataTab);
  setExpandState(false);
  setChatState(false);
  bindMaintEvents();
  initDataManager();
}

export function maintenanceLogin() {
  const u = dom.maintUser?.value.trim();
  const p = dom.maintPass?.value.trim();

  if (!u || !p) {
    toast("Vui lòng nhập tài khoản và mật khẩu");
    return;
  }

  legacyMaintAuthed = true;
  try {
    localStorage.removeItem("maint_authed");
    localStorage.removeItem("maint_emp_code");
    localStorage.removeItem("maint_profile");
  } catch {}
  showDash(true);
  toast("Đăng nhập bảo trì thành công (phiên tạm thời, không tự ghi nhớ)");
}

export function maintenanceLogout() {
  legacyMaintAuthed = false;
  try {
    localStorage.removeItem("maint_authed");
    localStorage.removeItem("maint_emp_code");
    localStorage.removeItem("maint_profile");
  } catch {}
  showDash(false);
  setChatState(false);
  setExpandState(false);
  toast("Đã đăng xuất");
}

export function fillDemo() {
  if (dom.maintUser) dom.maintUser.value = "engineer";
  if (dom.maintPass) dom.maintPass.value = "123456";
  if (dom.maintLan) dom.maintLan.value = "192.168.1.10";
}

export function switchDataTab(tab) {
  currentDataTab = tab === "mongo" ? "mongo" : "mysql";
  setActiveTabButton(currentDataTab);

  if (currentDataTab === "mongo") {
    toast("MongoDB sẽ được phát triển ở bước sau.");
  }
}

export function toggleDataExpand(force) {
  const next = typeof force === "boolean" ? force : !dataExpanded;
  setExpandState(next);
}

export function toggleMaintChat(force) {
  const currentOpen = dom.maintChatPanel?.classList.contains("open");
  const next = typeof force === "boolean" ? force : !currentOpen;
  setChatState(next);
}

export async function sendMaintChat() {
  if (maintChatBusy) return;

  const message = dom.maintChatInput?.value.trim();
  if (!message) return;

  appendMaintChat("user", message);
  if (dom.maintChatInput) dom.maintChatInput.value = "";

  maintChatBusy = true;
  if (dom.maintChatSend) dom.maintChatSend.disabled = true;

  try {
    const data = await api.chat(message);
    const answer = data?.answer || "Sunybot hiện chưa có phản hồi.";
    appendMaintChat("bot", answer);
  } catch (err) {
    appendMaintChat("bot", "Không thể kết nối chatbot lúc này.");
  } finally {
    maintChatBusy = false;
    if (dom.maintChatSend) dom.maintChatSend.disabled = false;
  }
}


