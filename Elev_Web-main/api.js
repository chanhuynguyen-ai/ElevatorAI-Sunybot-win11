/* ===== SUNYBOT AGENT + REALTIME INTEGRATION API SERVICE ===== */

const SESSION_KEY = 'sunybot_agent_session_id';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

function buildUrl(path) {
  if (!API_BASE_URL) return path;
  if (!path.startsWith('/')) return `${API_BASE_URL}/${path}`;
  return `${API_BASE_URL}${path}`;
}

function randomId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `suny-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function getAgentSessionId() {
  try {
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = randomId();
      localStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return randomId();
  }
}

export function resetAgentSessionId() {
  const id = randomId();
  try {
    localStorage.setItem(SESSION_KEY, id);
  } catch {}
  return id;
}

function saveAgentSessionId(nextId) {
  if (!nextId) return;
  try {
    localStorage.setItem(SESSION_KEY, nextId);
  } catch {}
}

async function parseJsonSafe(response) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return { raw: text };
  }
}

function normalizeCitation(citation, idx) {
  if (!citation) {
    return {
      id: `cit-${idx}`,
      source: 'knowledge_base',
      content: '',
      score: null,
    };
  }

  return {
    id: citation.id || `cit-${idx}`,
    source: citation.source || citation.title || 'knowledge_base',
    content: citation.content || citation.text || citation.snippet || '',
    score: typeof citation.score === 'number' ? citation.score : null,
  };
}

function normalizeToolTrace(trace, idx) {
  if (!trace) {
    return {
      id: `tool-${idx}`,
      tool_name: 'unknown_tool',
      args: {},
      status: 'ok',
      duration_ms: 0,
      summary: '',
    };
  }

  return {
    id: trace.id || `tool-${idx}`,
    tool_name: trace.tool_name || trace.tool || 'unknown_tool',
    args: trace.args || {},
    status: trace.status || 'ok',
    duration_ms: Number.isFinite(trace.duration_ms) ? trace.duration_ms : 0,
    summary: trace.summary || trace.result || '',
  };
}

export function normalizeAgentResponse(raw = {}, fallbackMessage = '') {
  const answer =
    raw.answer ||
    raw.response ||
    raw.final_answer ||
    raw.message ||
    'Sunybot chưa có phản hồi.';

  const normalized = {
    answer,
    source: raw.source || 'agent',
    intent: raw.intent || null,
    confidence: typeof raw.confidence === 'number' ? raw.confidence : null,
    session_id: raw.session_id || getAgentSessionId(),
    tool_trace: Array.isArray(raw.tool_trace)
      ? raw.tool_trace.map(normalizeToolTrace)
      : [],
    citations: Array.isArray(raw.citations)
      ? raw.citations.map(normalizeCitation)
      : [],
    memory_summary: raw.memory_summary || '',
    requires_human: Boolean(raw.requires_human),
    status: raw.status || 'ok',
    request_message: fallbackMessage,
    raw,
  };

  saveAgentSessionId(normalized.session_id);
  return normalized;
}

async function requestJson(path, options = {}) {
  const response = await fetch(buildUrl(path), options);
  const data = await parseJsonSafe(response);

  if (!response.ok) {
    const err = new Error(data?.error || data?.detail || `HTTP ${response.status}`);
    err.status = response.status;
    err.payload = data;
    throw err;
  }

  return data;
}

async function requestFirstSuccess(attempts = []) {
  let lastError = null;

  for (const attempt of attempts) {
    try {
      return await requestJson(attempt.url, attempt.options);
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error('Không thể kết nối backend');
}

function buildChatPayload(message, extra = {}) {
  return {
    message,
    question: message,
    session_id: extra.session_id || getAgentSessionId(),
    employee_id: extra.employee_id || '',
    employee_name: extra.employee_name || '',
    scope: extra.scope,
    persona: extra.persona,
    include_trace: extra.include_trace,
  };
}

export async function fetchChatAbortable(message, signal, extra = {}) {
  const data = await requestJson('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildChatPayload(message, extra)),
    signal,
  });

  return normalizeAgentResponse(data, message);
}

const api = {
  elevatorStatus: () => requestJson('/api/elevator/status'),
  weather: () => requestJson('/api/weather'),
  agentStatus: () => requestJson('/status'),
  health: () => requestJson('/health'),

  chat: async (message, extra = {}) => {
    const data = await requestJson('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildChatPayload(message, extra)),
    });

    return normalizeAgentResponse(data, message);
  },

  maintenanceChat: async (message, extra = {}) => {
    const data = await requestFirstSuccess([
      {
        url: '/api/chat/maintenance',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            buildChatPayload(message, {
              ...extra,
              scope: 'maintenance',
              persona: 'maintenance_console',
              include_trace: true,
            })
          ),
        },
      },
      {
        url: '/chat',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            buildChatPayload(message, {
              ...extra,
              scope: 'maintenance',
              persona: 'maintenance_console',
              include_trace: true,
            })
          ),
        },
      },
    ]);

    return normalizeAgentResponse(data, message);
  },

  maintenanceLogin: (payload) =>
    requestFirstSuccess([
      {
        url: '/api/integration/users/login',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      },
      {
        url: '/api/maintenance/login',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      },
    ]),

  maintenanceRegister: (payload) =>
    requestFirstSuccess([
      {
        url: '/api/integration/users/register',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      },
      {
        url: '/api/maintenance/register',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      },
    ]),

  command: async ({
    elevator_id = 1,
    from_floor = null,
    target_floor = null,
    direction = 'up',
  } = {}) => {
    return requestFirstSuccess([
      {
        url: '/command',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ elevator_id, from_floor, target_floor, direction }),
        },
      },
      {
        url: '/api/elevator/call',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ floor: target_floor ?? from_floor, direction }),
        },
      },
    ]);
  },

  callFloor: async (floor) => {
    const result = await api.command({ target_floor: floor, direction: 'up' });
    try {
      localStorage.setItem('lift_target', String(floor));
    } catch {}
    return result;
  },

  sos: async (payload = {}) => {
    return requestFirstSuccess([
      {
        url: '/api/sos',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      },
      {
        url: '/chat',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: `Kích hoạt SOS khẩn cấp cho thang máy ${payload.elevator || 'A'} tại tầng ${payload.floor || '--'}`,
            session_id: getAgentSessionId(),
          }),
        },
      },
    ]);
  },

  cvConfig: () => requestJson('/api/integration/cv/config'),
  cvStatus: () => requestJson('/api/integration/cv/status'),
  cvEvents: (limit = 20) =>
    requestJson(`/api/integration/cv/events?limit=${encodeURIComponent(limit)}`),
  cvDensity: (days = 7) =>
    requestJson(`/api/integration/cv/density?days=${encodeURIComponent(days)}`),
  cvStreamUrl: () => requestJson('/api/integration/cv/stream-url'),

  unknownFaceCandidates: (limit = 10) =>
    requestJson(`/api/integration/cv/unknown-candidates?limit=${encodeURIComponent(limit)}`),

  registerFace: async (payload) => {
    const employeeCode = String(payload?.employee_id || payload?.employee_code || '').trim();
    const employeeName = String(payload?.employee_name || payload?.full_name || '').trim();
    const normalizedPayload = {
      ...payload,
      employee_id: employeeCode,
      employee_code: employeeCode,
      employee_name: employeeName,
      full_name: employeeName,
      department: String(payload?.department || '').trim() || 'Kỹ thuật',
    };

    return requestFirstSuccess([
      {
        url: '/api/integration/cv/register-face',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(normalizedPayload),
        },
      },
      {
        url: '/api/cv/register-face',
        options: {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(normalizedPayload),
        },
      },
    ]);
  },

  dataCatalog: () => requestJson('/api/integration/data/catalog'),

  dataTables: (database) =>
    requestJson(`/api/integration/data/tables?database=${encodeURIComponent(database)}`),

  dataTable: (database, table, limit = 50, offset = 0) =>
    requestJson(
      `/api/integration/data/table?database=${encodeURIComponent(database)}&table=${encodeURIComponent(table)}&limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`
    ),

  saveDataRow: (database, table, row) =>
    requestJson('/api/integration/data/row/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ database, table, row }),
    }),

  deleteDataRow: (database, table, keys) =>
    requestJson('/api/integration/data/row/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ database, table, keys }),
    }),
};

export default api;