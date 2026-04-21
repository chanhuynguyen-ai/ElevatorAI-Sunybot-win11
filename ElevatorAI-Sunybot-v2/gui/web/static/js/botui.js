// gui/web/static/js/botui.js
export function setBotMode(elShell, elLabel, mode) {
  if (!elShell || !elLabel) return;

  elShell.classList.remove("listening", "speaking");

  if (mode === "listening") {
    elShell.classList.add("listening");
    elLabel.textContent = "Chế độ: Đang nghe";
  } else if (mode === "speaking") {
    elShell.classList.add("speaking");
    elLabel.textContent = "Chế độ: Đang trả lời";
  } else {
    elLabel.textContent = "Chế độ: Bình thường";
  }
}

export function speak(text) {
  if (!window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "vi-VN";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
}
