// gui/web/static/js/status.js
import { dom } from "./dom.js";
import { api } from "./api.js";

function hhmm() {
  const d = new Date();
  return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0");
}

export async function updateStatus() {
  try {
    const s = await api.elevatorStatus();

    if (dom.floor) dom.floor.textContent = s.floor ?? "--";
    if (dom.clock) dom.clock.textContent = s.time ?? "--:--:--";
    if (dom.people) dom.people.textContent = s.people_count ?? "--";
    if (dom.door) dom.door.textContent = s.door ?? "--";

    if (dom.tb_people) dom.tb_people.textContent = s.people_count ?? "--";

    const dir = s.direction || "--";
    if (dom.direction) {
      dom.direction.textContent =
        dir === "UP" ? "↑ Lên" : dir === "DOWN" ? "↓ Xuống" : "Đứng";
    }

    if (dom.overload) {
      if (s.overload) {
        dom.overload.textContent = "QUÁ TẢI";
        dom.overload.className = "badge err";
      } else {
        dom.overload.textContent = "Bình thường";
        dom.overload.className = "badge ok";
      }
    }

    // maint mirror
    if (dom.maintFloor) dom.maintFloor.textContent = s.floor ?? "--";
    if (dom.maintDirection) dom.maintDirection.textContent = dir;
    if (dom.maintDoor) dom.maintDoor.textContent = s.door ?? "--";
    if (dom.maintPeople) dom.maintPeople.textContent = s.people_count ?? "--";
    if (dom.maintTime) dom.maintTime.textContent = hhmm();

    if (dom.sosStatus) dom.sosStatus.textContent = `Trạng thái: ${s.door ?? "--"}`;
  } catch (e) {
    // im lặng để UI vẫn mượt
  }
}
