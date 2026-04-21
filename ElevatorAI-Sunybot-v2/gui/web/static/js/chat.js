// gui/web/static/js/chat.js
import { dom } from "./dom.js";
import { api } from "./api.js";
import { setBotMode, speak } from "./botui.js";

const CHAT_SESSION_KEY = "sunybot_agent_session_id";

function createSessionId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getSessionId() {
  try {
    let sessionId = localStorage.getItem(CHAT_SESSION_KEY);
    if (!sessionId) {
      sessionId = createSessionId();
      localStorage.setItem(CHAT_SESSION_KEY, sessionId);
    }
    return sessionId;
  } catch {
    return createSessionId();
  }
}

function updateSessionId(sessionId) {
  if (!sessionId) return;
  try {
    localStorage.setItem(CHAT_SESSION_KEY, sessionId);
  } catch {
    // ignore storage errors
  }
}

function scrollChatToBottom() {
  if (!dom.chatMessages) return;
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

function createBubble(who) {
  const div = document.createElement("div");
  div.className = `bubble ${who}`;
  return div;
}

function createSectionTitle(text) {
  const title = document.createElement("div");
  title.textContent = text;
  title.style.marginTop = "10px";
  title.style.fontSize = "12px";
  title.style.fontWeight = "700";
  title.style.opacity = "0.9";
  return title;
}

function createMutedText(text) {
  const node = document.createElement("div");
  node.textContent = text;
  node.style.fontSize = "12px";
  node.style.opacity = "0.82";
  node.style.marginTop = "6px";
  node.style.whiteSpace = "pre-wrap";
  return node;
}

function createBadge(text) {
  const badge = document.createElement("span");
  badge.textContent = text;
  badge.style.display = "inline-block";
  badge.style.fontSize = "11px";
  badge.style.padding = "3px 8px";
  badge.style.margin = "6px 6px 0 0";
  badge.style.borderRadius = "999px";
  badge.style.background = "rgba(255,255,255,0.12)";
  badge.style.border = "1px solid rgba(255,255,255,0.16)";
  return badge;
}

function formatConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  return `${Math.round(value * 100)}%`;
}

function shortenSessionId(sessionId) {
  if (!sessionId) return null;
  if (sessionId.length <= 14) return sessionId;
  return `${sessionId.slice(0, 8)}...${sessionId.slice(-4)}`;
}

function normalizeToolTrace(toolTrace) {
  return Array.isArray(toolTrace) ? toolTrace : [];
}

function normalizeCitations(citations) {
  return Array.isArray(citations) ? citations : [];
}

export function appendMessage(text, who) {
  if (!dom.chatMessages) return;
  const bubble = createBubble(who);
  bubble.textContent = text;
  dom.chatMessages.appendChild(bubble);
  scrollChatToBottom();
}

function appendAgentResponse(data) {
  if (!dom.chatMessages) return;

  const bubble = createBubble("bot");

  const answer = document.createElement("div");
  answer.textContent = data.answer || "...";
  answer.style.whiteSpace = "pre-wrap";
  bubble.appendChild(answer);

  const badgeRow = document.createElement("div");
  badgeRow.style.marginTop = "8px";

  const badgeTexts = [];
  if (data.intent) badgeTexts.push(`Intent: ${data.intent}`);
  const confidence = formatConfidence(data.confidence);
  if (confidence) badgeTexts.push(`Tin cậy: ${confidence}`);
  if (data.source) badgeTexts.push(`Nguồn: ${data.source}`);
  const shortSession = shortenSessionId(data.session_id);
  if (shortSession) badgeTexts.push(`Session: ${shortSession}`);
  if (data.requires_human) badgeTexts.push("Cần người hỗ trợ");

  badgeTexts.forEach((text) => badgeRow.appendChild(createBadge(text)));
  if (badgeTexts.length > 0) bubble.appendChild(badgeRow);

  const toolTrace = normalizeToolTrace(data.tool_trace);
  if (toolTrace.length > 0) {
    bubble.appendChild(createSectionTitle("Công cụ đã dùng"));
    toolTrace.forEach((item, index) => {
      const lineParts = [
        `${index + 1}. ${item.tool_name || "unknown"}`,
        item.status ? `[${item.status}]` : "",
        typeof item.duration_ms === "number" ? `${item.duration_ms}ms` : "",
      ].filter(Boolean);

      const line = createMutedText(lineParts.join(" • "));
      bubble.appendChild(line);

      if (item.summary) {
        bubble.appendChild(createMutedText(`↳ ${item.summary}`));
      }

      const args = item.args && Object.keys(item.args).length > 0 ? JSON.stringify(item.args, null, 2) : "";
      if (args) {
        const pre = document.createElement("pre");
        pre.textContent = args;
        pre.style.margin = "6px 0 0 0";
        pre.style.padding = "8px";
        pre.style.fontSize = "11px";
        pre.style.whiteSpace = "pre-wrap";
        pre.style.borderRadius = "10px";
        pre.style.background = "rgba(0,0,0,0.15)";
        bubble.appendChild(pre);
      }
    });
  }

  const citations = normalizeCitations(data.citations);
  if (citations.length > 0) {
    bubble.appendChild(createSectionTitle("Dữ liệu tham chiếu"));
    citations.forEach((item, index) => {
      const source = item.source || `Nguồn ${index + 1}`;
      const scoreText = typeof item.score === "number" ? ` • score ${item.score.toFixed(2)}` : "";
      bubble.appendChild(createMutedText(`${index + 1}. ${source}${scoreText}`));
      if (item.content) {
        bubble.appendChild(createMutedText(item.content));
      }
    });
  }

  if (data.memory_summary) {
    bubble.appendChild(createSectionTitle("Ngữ cảnh phiên"));
    bubble.appendChild(createMutedText(data.memory_summary));
  }

  dom.chatMessages.appendChild(bubble);
  scrollChatToBottom();
}

function setChatState(text) {
  if (dom.stateChat) dom.stateChat.textContent = text;
}

function buildStateText(data) {
  const parts = ["Đã trả lời"];

  const toolCount = Array.isArray(data.tool_trace) ? data.tool_trace.length : 0;
  if (toolCount > 0) {
    parts.push(`${toolCount} tool`);
  }

  if (data.intent) {
    parts.push(data.intent);
  }

  if (data.requires_human) {
    parts.push("cần hỗ trợ người thật");
  }

  return parts.join(" • ") + ".";
}

export async function sendChat() {
  const input = dom.chatInput;
  if (!input) return;

  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  appendMessage(message, "user");

  setBotMode(dom.botShellChat, dom.botModeChat, "speaking");
  setChatState("Đang để agent phân tích và trả lời...");

  try {
    const sessionId = getSessionId();
    const data = await api.chat({ message, session_id: sessionId });
    updateSessionId(data.session_id || sessionId);
    appendAgentResponse(data);
    setChatState(buildStateText(data));
    if (data.answer) {
      speak(data.answer);
    }
  } catch (e) {
    appendMessage(`Sunybot hiện không thể trả lời. ${e?.message || ""}`.trim(), "bot");
    setChatState("Lỗi kết nối hoặc lỗi agent.");
  } finally {
    setBotMode(dom.botShellChat, dom.botModeChat, "idle");
  }
}

export function quickAsk(text) {
  if (!dom.chatInput) return;
  dom.chatInput.value = text;
  sendChat();
}

export function resetChatSession() {
  const sessionId = createSessionId();
  updateSessionId(sessionId);
  setChatState("Đã tạo phiên hội thoại mới.");
}
