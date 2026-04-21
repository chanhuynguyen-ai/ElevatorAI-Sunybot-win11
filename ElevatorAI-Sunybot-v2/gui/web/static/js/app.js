// gui/web/static/js/app.js
import { updateStatus } from "./status.js";
import { updateWeather } from "./weather.js";
import { enableWake, voiceChatOnce } from "./voice.js";
import { sendChat, quickAsk, appendMessage } from "./chat.js";
import { callFloor, confirmCall } from "./call.js";
import { updateSOSTime, sendSOS } from "./sos.js";
import { initMaint, maintenanceLogin, maintenanceLogout, fillDemo, runLLMQuery } from "./maint.js";
import { dom } from "./dom.js";

function hhmm(){
  const d = new Date();
  return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0");
}

function initNav(){
  const navButtons = document.querySelectorAll(".nav-btn");
  navButtons.forEach(btn => btn.addEventListener("click", () => {
    navButtons.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.getAttribute("data-screen");
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    document.getElementById(`screen-${target}`)?.classList.add("active");
  }));
}

function bindGlobalFunctions(){
  // để HTML onclick="..." vẫn chạy mà không viết inline logic
  window.callFloor = callFloor;
  window.confirmCall = confirmCall;
  window.sendSOS = sendSOS;

  window.sendChat = sendChat;
  window.quickAsk = quickAsk;

  window.voiceChat = () => {
    voiceChatOnce((t)=>{
      appendMessage(t, "user");
      if(dom.chatInput) dom.chatInput.value = t;
      sendChat();
    });
  };

  window.maintenanceLogin = maintenanceLogin;
  window.maintenanceLogout = maintenanceLogout;
  window.fillDemo = fillDemo;
  window.runLLMQuery = runLLMQuery;
}

function initTopbarClock(){
  if (dom.tb_time) dom.tb_time.textContent = hhmm();
  setInterval(()=>{ if(dom.tb_time) dom.tb_time.textContent = hhmm(); }, 1000);
}

function boot(){
  initNav();
  bindGlobalFunctions();
  initTopbarClock();

  initMaint();

  // status + weather loop
  updateStatus();
  setInterval(updateStatus, 1000);

  updateWeather();
  setInterval(updateWeather, 10*60*1000);

  updateSOSTime();
  setInterval(updateSOSTime, 1000);

  // start wake-word
  enableWake();
}

boot();
