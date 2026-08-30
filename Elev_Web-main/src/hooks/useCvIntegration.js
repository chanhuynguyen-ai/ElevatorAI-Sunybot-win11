import { useEffect, useMemo, useState } from 'react';
import api from '../services/api';

function normalizeNumber(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function severityToUiType(severity) {
  const v = String(severity || '').toLowerCase();
  if (v === 'critical' || v === 'high' || v === 'error') return 'error';
  if (v === 'medium' || v === 'warn' || v === 'warning') return 'warn';
  return 'info';
}

function normalizeStatus(raw = {}) {
  return {
    available: Boolean(raw.available),
    camera_online: Boolean(raw.camera_online),
    cam_id: raw.cam_id || 'cam_01',
    fps: normalizeNumber(raw.fps, 0),
    people_count: normalizeNumber(raw.people_count, 0),
    backend: raw.backend || 'cv_service',
    source: raw.source || 'cv_service',
    last_event_type: raw.last_event_type || null,
    last_event_title: raw.last_event_title || raw.last_event_type || 'Chưa có sự kiện',
    last_event_at: raw.last_event_at || null,
    stream_url: raw.stream_url || '',
    error: raw.error || '',
    raw,
  };
}

function normalizeEvent(raw = {}, idx = 0) {
  return {
    id: raw.id || `cv-event-${idx}`,
    timestamp: raw.timestamp || raw.created_at || null,
    cam_id: raw.cam_id || 'cam_01',
    type: raw.type || 'UNKNOWN',
    title: raw.title || raw.type || 'Sự kiện CV',
    severity: raw.severity || 'info',
    uiType: severityToUiType(raw.severity),
    confidence: Number.isFinite(Number(raw.confidence)) ? Number(raw.confidence) : null,
    people_count: Number.isFinite(Number(raw.people_count)) ? Number(raw.people_count) : null,
    person_name: raw.person_name || null,
    track_id: raw.track_id || null,
    posture: raw.posture || null,
    raw,
  };
}

export default function useCvIntegration({
  enabled = true,
  eventsLimit = 20,
  statusIntervalMs = 2000,
  eventsIntervalMs = 4000,
} = {}) {
  const [status, setStatus] = useState(() => normalizeStatus({}));
  const [events, setEvents] = useState([]);
  const [streamUrl, setStreamUrl] = useState('');
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;

    const loadStreamUrl = async () => {
      try {
        const data = await api.cvStreamUrl();
        if (!cancelled) {
          setStreamUrl(data.stream_url || data.upstream_stream_url || '');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || String(err));
        }
      }
    };

    const loadStatus = async () => {
      try {
        const data = await api.cvStatus();
        if (cancelled) return;
        const nextStatus = normalizeStatus(data);
        setStatus(nextStatus);
        if (nextStatus.stream_url) setStreamUrl(nextStatus.stream_url);
        setLoadingStatus(false);
        setError(nextStatus.error || '');
      } catch (err) {
        if (!cancelled) {
          setLoadingStatus(false);
          setError(err.message || String(err));
          setStatus((prev) =>
            normalizeStatus({
              ...prev,
              available: false,
              camera_online: false,
              error: err.message || String(err),
            }),
          );
        }
      }
    };

    const loadEvents = async () => {
      try {
        const data = await api.cvEvents(eventsLimit);
        if (cancelled) return;
        const items = Array.isArray(data?.items) ? data.items.map(normalizeEvent) : [];
        setEvents(items);
        setLoadingEvents(false);
      } catch (err) {
        if (!cancelled) {
          setLoadingEvents(false);
          setError(err.message || String(err));
          setEvents([]);
        }
      }
    };

    loadStreamUrl();
    loadStatus();
    loadEvents();

    const statusTimer = window.setInterval(loadStatus, statusIntervalMs);
    const eventsTimer = window.setInterval(loadEvents, eventsIntervalMs);
    const streamTimer = window.setInterval(loadStreamUrl, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(statusTimer);
      window.clearInterval(eventsTimer);
      window.clearInterval(streamTimer);
    };
  }, [enabled, eventsLimit, statusIntervalMs, eventsIntervalMs]);

  const latestEvent = useMemo(() => events[0] || null, [events]);

  return {
    status,
    events,
    latestEvent,
    streamUrl,
    loadingStatus,
    loadingEvents,
    error,
  };
}