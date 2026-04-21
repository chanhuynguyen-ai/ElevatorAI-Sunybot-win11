// gui/web/static/js/weather.js
import { dom } from "./dom.js";
import { api } from "./api.js";

export async function updateWeather() {
  try {
    const w = await api.weather(); // {text, temp}
    const text = `${w.text} ${w.temp}°C`;

    if (dom.weather) dom.weather.textContent = text;
    if (dom.tb_weather) dom.tb_weather.textContent = text;
  } catch (e) {
    if (dom.weather) dom.weather.textContent = "--";
    if (dom.tb_weather) dom.tb_weather.textContent = "--";
  }
}
