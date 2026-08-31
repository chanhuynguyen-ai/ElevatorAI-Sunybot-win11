const LOCKED_FLOORS_KEY = 'locked_floors';
const FLOOR_AUTH_CONFIG_KEY = 'floor_auth_config';
const FLOOR_PINS_KEY = 'floor_pins';
const FLOOR_QR_RULES_KEY = 'floor_qr_rules';
const MAINT_TIMELINE_KEY = 'maintenance_timeline';

export const ALL_FLOORS = Array.from({ length: 15 }, (_, index) => index + 1);
export const DEFAULT_LOCKED_FLOORS = [5, 6, 7];

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function emitAccessChange(key, value) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent('elevator-access-updated', {
      detail: { key, value, timestamp: new Date().toISOString() },
    })
  );
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
  emitAccessChange(key, value);
  return value;
}

function normalizeFloorList(floors) {
  return [...new Set((floors || []).map(Number).filter((value) => Number.isFinite(value) && value >= 1 && value <= 15))].sort((a, b) => a - b);
}

function migrateAuthConfig(config = {}) {
  const migrated = {};
  Object.entries(config || {}).forEach(([floor, value]) => {
    const item = value && typeof value === 'object' ? value : {};
    migrated[String(floor)] = {
      pin: item.pin !== false,
      qr: Boolean(item.qr || item.face),
    };
  });
  return migrated;
}

function normalizeQrRules(rules = {}) {
  const next = {};
  Object.entries(rules || {}).forEach(([floor, value]) => {
    next[String(floor)] = {
      allowedTokens: parseDelimitedList(value?.allowedTokens || value?.tokens || []),
      allowedEmployeeIds: parseDelimitedList(value?.allowedEmployeeIds || value?.employees || []),
    };
  });
  return next;
}

export function getLockedFloors() {
  return normalizeFloorList(readJson(LOCKED_FLOORS_KEY, DEFAULT_LOCKED_FLOORS));
}

export function setLockedFloors(floors) {
  return writeJson(LOCKED_FLOORS_KEY, normalizeFloorList(floors));
}

export function getFloorAuthConfig() {
  return migrateAuthConfig(readJson(FLOOR_AUTH_CONFIG_KEY, {}));
}

export function setFloorAuthConfig(config) {
  return writeJson(FLOOR_AUTH_CONFIG_KEY, migrateAuthConfig(config));
}

export function getFloorPins() {
  return readJson(FLOOR_PINS_KEY, {});
}

export function setFloorPins(pins) {
  return writeJson(FLOOR_PINS_KEY, pins || {});
}

export function getFloorQrRules() {
  return normalizeQrRules(readJson(FLOOR_QR_RULES_KEY, {}));
}

export function setFloorQrRules(rules) {
  return writeJson(FLOOR_QR_RULES_KEY, normalizeQrRules(rules));
}

export function saveFloorQrRule(floor, rule) {
  const current = getFloorQrRules();
  current[String(floor)] = {
    allowedTokens: parseDelimitedList(rule?.allowedTokens || []),
    allowedEmployeeIds: parseDelimitedList(rule?.allowedEmployeeIds || []),
  };
  return setFloorQrRules(current);
}

export function parseDelimitedList(input) {
  if (Array.isArray(input)) {
    return [...new Set(input.map((item) => String(item || '').trim()).filter(Boolean))];
  }
  return [...new Set(String(input || '').split(/[\n,;]+/).map((item) => item.trim()).filter(Boolean))];
}

export function appendMaintenanceTimeline(entry = {}) {
  const current = readJson(MAINT_TIMELINE_KEY, []);
  const item = {
    id: entry.id || `evt-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    timestamp: entry.timestamp || new Date().toISOString(),
    title: entry.title || 'Sự kiện hệ thống',
    severity: entry.severity || 'info',
    source: entry.source || 'maintenance_ui',
    location: entry.location || 'Trung tâm bảo trì',
    actor: entry.actor || '',
    extra: entry.extra || {},
  };
  const next = [item, ...current].slice(0, 200);
  writeJson(MAINT_TIMELINE_KEY, next);
  return item;
}

export function getMaintenanceTimeline(limit = 60) {
  return readJson(MAINT_TIMELINE_KEY, []).slice(0, limit);
}

export function subscribeAccessChange(listener) {
  if (typeof window === 'undefined') return () => {};

  const customHandler = (event) => {
    listener(event?.detail || null);
  };

  const storageHandler = (event) => {
    if (
      event.key === LOCKED_FLOORS_KEY ||
      event.key === FLOOR_AUTH_CONFIG_KEY ||
      event.key === FLOOR_PINS_KEY ||
      event.key === FLOOR_QR_RULES_KEY ||
      event.key === MAINT_TIMELINE_KEY
    ) {
      listener({ key: event.key, value: event.newValue, source: 'storage' });
    }
  };

  window.addEventListener('elevator-access-updated', customHandler);
  window.addEventListener('storage', storageHandler);

  return () => {
    window.removeEventListener('elevator-access-updated', customHandler);
    window.removeEventListener('storage', storageHandler);
  };
}

export function parseQrPayload(rawValue) {
  const raw = String(rawValue || '').trim();
  if (!raw) {
    return {
      raw: '',
      token: '',
      employee_id: '',
      employee_name: '',
      department: '',
    };
  }

  if (raw.startsWith('{') && raw.endsWith('}')) {
    try {
      const parsed = JSON.parse(raw);
      return {
        raw,
        token: String(parsed.token || parsed.qr_token || parsed.code || raw).trim(),
        employee_id: String(parsed.employee_id || parsed.employee_code || parsed.staff_id || '').trim(),
        employee_name: String(parsed.employee_name || parsed.full_name || parsed.name || '').trim(),
        department: String(parsed.department || '').trim(),
      };
    } catch {}
  }

  const segments = raw.split('|').map((item) => item.trim()).filter(Boolean);
  if (segments.some((item) => item.includes(':'))) {
    const data = {};
    segments.forEach((segment) => {
      const [left, ...rest] = segment.split(':');
      if (!left || !rest.length) return;
      data[left.trim().toLowerCase()] = rest.join(':').trim();
    });
    return {
      raw,
      token: String(data.token || data.code || raw).trim(),
      employee_id: String(data.employee_id || data.employee_code || data.staff || '').trim(),
      employee_name: String(data.employee_name || data.name || '').trim(),
      department: String(data.department || '').trim(),
    };
  }

  return {
    raw,
    token: raw,
    employee_id: '',
    employee_name: '',
    department: '',
  };
}

export function isQrAuthorizedForFloor(floor, payload) {
  const rules = getFloorQrRules();
  const currentRule = rules[String(floor)] || { allowedTokens: [], allowedEmployeeIds: [] };
  const token = String(payload?.token || '').trim().toLowerCase();
  const employeeId = String(payload?.employee_id || '').trim().toLowerCase();

  const allowedTokens = parseDelimitedList(currentRule.allowedTokens).map((item) => item.toLowerCase());
  const allowedEmployees = parseDelimitedList(currentRule.allowedEmployeeIds).map((item) => item.toLowerCase());

  if (!allowedTokens.length && !allowedEmployees.length) {
    return false;
  }

  if (token && allowedTokens.some((item) => item === '*' || item === token)) {
    return true;
  }

  if (employeeId && allowedEmployees.some((item) => item === '*' || item === employeeId)) {
    return true;
  }

  return false;
}
