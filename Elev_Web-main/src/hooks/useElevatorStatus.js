import { useEffect, useState } from 'react';
import api from '../services/api';

const DEFAULT_THRESHOLD = Number(import.meta.env.VITE_OVERLOAD_THRESHOLD || 4);

const DEFAULT_STATUS = {
  elevator_id: 1,
  floor: '--',
  direction: '--',
  door: '--',
  people_count: '--',
  overload: false,
  overload_threshold: DEFAULT_THRESHOLD,
  status: 'UNKNOWN',
  time: '--:--:--',
  source: 'frontend_default',
  error: null,
};

function toNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeStatus(payload = {}) {
  const nowText = new Date().toLocaleTimeString('vi-VN');
  const peopleCount = toNumber(payload.people_count ?? payload.person_count ?? payload.occupancy);
  const overloadThreshold = toNumber(payload.overload_threshold) ?? DEFAULT_THRESHOLD;
  const overloadByStatus = String(payload.status || '').toUpperCase().includes('OVERLOAD');
  const overload =
    Boolean(payload.overload) ||
    overloadByStatus ||
    (peopleCount !== null && peopleCount >= overloadThreshold);

  return {
    elevator_id: payload.elevator_id ?? 1,
    floor: payload.floor ?? '--',
    direction: payload.direction ?? '--',
    door: payload.door ?? '--',
    people_count: peopleCount ?? payload.people_count ?? '--',
    overload,
    overload_threshold: overloadThreshold,
    status: payload.status || (overload ? 'OVERLOAD' : 'UNKNOWN'),
    time: payload.time || nowText,
    source: payload.source || 'backend',
    error: payload.error || null,
    camera_online: payload.camera_online ?? null,
    cv_available: payload.cv_available ?? null,
    last_event_type: payload.last_event_type || null,
  };
}

export default function useElevatorStatus(intervalMs = 1000) {
  const [status, setStatus] = useState(DEFAULT_STATUS);

  useEffect(() => {
    let alive = true;
    let timerId = null;

    const loadStatus = async () => {
      try {
        const data = await api.elevatorStatus();
        if (!alive) return;

        setStatus((prev) => ({
          ...prev,
          ...normalizeStatus(data),
        }));
      } catch (err) {
        if (!alive) return;

        setStatus((prev) => ({
          ...prev,
          time: new Date().toLocaleTimeString('vi-VN'),
          source: 'backend_error',
          error: err?.message || 'Không thể lấy trạng thái thang máy',
        }));
      }
    };

    loadStatus();
    timerId = setInterval(loadStatus, Math.max(500, intervalMs));

    return () => {
      alive = false;
      if (timerId) clearInterval(timerId);
    };
  }, [intervalMs]);

  return status;
}
