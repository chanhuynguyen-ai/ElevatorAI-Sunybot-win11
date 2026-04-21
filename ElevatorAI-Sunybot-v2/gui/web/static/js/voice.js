// gui/web/static/js/voice.js
import { dom } from "./dom.js";
import { api } from "./api.js";
import { setBotMode, speak } from "./botui.js";

let recWake = null;
let recChat = null;

export function enableWake() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (dom.state) dom.state.textContent = "Không hỗ trợ STT trên trình duyệt này.";
    return;
  }

  recWake = new SpeechRecognition();
  recWake.lang = "vi-VN";
  recWake.continuous = true;
  recWake.interimResults = true;

  recWake.onstart = () => {
    setBotMode(dom.botShell, dom.botMode, "listening");
    if (dom.state) dom.state.textContent = "Đang nghe wake word…";
  };

  recWake.onerror = () => {
    setBotMode(dom.botShell, dom.botMode, "idle");
    if (dom.state) dom.state.textContent = "Mic lỗi — tự khôi phục...";
    setTimeout(() => { try { recWake.start(); } catch {} }, 800);
  };

  recWake.onend = () => {
    setBotMode(dom.botShell, dom.botMode, "idle");
    setTimeout(() => { try { recWake.start(); } catch {} }, 350);
  };

  let lastFinal = "";
  recWake.onresult = async (ev) => {
    let transcript = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      transcript += ev.results[i][0].transcript;
    }
    transcript = transcript.trim().toLowerCase();

    const last = ev.results[ev.results.length - 1];
    if (!last || !last.isFinal) return;

    if (transcript === lastFinal) return;
    lastFinal = transcript;

    if (transcript.includes("hey sunybot") || transcript.includes("hey sunnybot")) {
      const after = transcript
        .replace("hey sunybot", "")
        .replace("hey sunnybot", "")
        .trim();

      if (!after) {
        if (dom.state) dom.state.textContent = "Đã kích hoạt. Hãy nói câu lệnh...";
        return;
      }

      if (dom.state) dom.state.textContent = "Đang xử lý: " + after;
      setBotMode(dom.botShell, dom.botMode, "speaking");

      try {
        const data = await api.chat(after);
        const answer = data.answer || "...";
        if (dom.state) dom.state.textContent = "Sunybot: " + answer;
        speak(answer);
      } catch {
        if (dom.state) dom.state.textContent = "Sunybot hiện không thể trả lời.";
      } finally {
        setBotMode(dom.botShell, dom.botMode, "listening");
      }
    }
  };

  try { recWake.start(); } catch {}
}

export function voiceChatOnce(onText) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast?.("Không hỗ trợ STT");
    return;
  }

  if (recWake) { try { recWake.stop(); } catch {} }

  recChat = new SpeechRecognition();
  recChat.lang = "vi-VN";
  recChat.continuous = false;
  recChat.interimResults = false;

  recChat.onresult = (ev) => {
    const transcript = ev.results[0][0].transcript.trim();
    onText?.(transcript);
  };

  recChat.onerror = () => {
    if (recWake) { try { recWake.start(); } catch {} }
  };

  recChat.onend = () => {
    if (recWake) { try { recWake.start(); } catch {} }
  };

  try { recChat.start(); } catch {}
}
