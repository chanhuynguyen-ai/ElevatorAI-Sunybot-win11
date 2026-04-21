import { api } from "./api.js";

export async function callFloor(floor, locked=false){
  if(locked){ showToast?.("Tầng bị khóa. Cần xác thực."); return; }
  try{ await api.callFloor(floor); showToast?.(`Đã gọi tầng ${floor}`); }
  catch{ showToast?.("Không thể gọi tầng"); }
}

export async function confirmCall(floor){
  return callFloor(floor, false);
}
