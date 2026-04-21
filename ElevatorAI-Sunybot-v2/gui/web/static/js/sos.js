import { dom } from "./dom.js";
import { api } from "./api.js";

export function updateSOSTime(){
  if (!dom.sosTime) return;
  dom.sosTime.textContent = new Date().toLocaleTimeString("vi-VN");
}

export async function sendSOS(){
  updateSOSTime();
  try{
    await api.sos({
      elevator:"A",
      time: new Date().toISOString(),
      floor: dom.floor?.textContent ?? "--",
      status: dom.door?.textContent ?? "--"
    });
    showToast?.("Đã gửi tín hiệu SOS");
  }catch{
    showToast?.("Không thể gửi SOS");
  }
}
