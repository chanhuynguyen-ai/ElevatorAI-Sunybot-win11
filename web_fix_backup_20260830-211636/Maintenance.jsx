import React, { useEffect, useMemo, useState } from 'react';
import useElevatorStatus from '../hooks/useElevatorStatus';
import useClock from '../hooks/useClock';
import { useToast } from '../components/Toast';
import AgentTracePanel from '../components/AgentTracePanel';
import api, { getAgentSessionId, resetAgentSessionId } from '../services/api';
import './Maintenance.css';

const ALL_FLOORS = Array.from({ length: 15 }, (_, i) => i + 1);

const DATASET_OPTIONS = {
  elevator_cv: [
    { key: 'camera_events', label: 'camera_events' },
    { key: 'camera_occupancy_samples', label: 'camera_occupancy_samples' },
    { key: 'person_registry', label: 'person_registry' },
    { key: 'face_embeddings', label: 'face_embeddings' },
  ],
  elevator_llm: [
    { key: 'employees', label: 'employees' },
    { key: 'intents', label: 'intents' },
    { key: 'prompts', label: 'prompts' },
    { key: 'answers', label: 'answers' },
  ],
  elevator_user: [
    { key: 'maintenance_users', label: 'maintenance_users' },
  ],
};

const QUICK_PROMPTS = [
  'Tóm tắt lỗi nổi bật hôm nay',
  'Lỗi nào xuất hiện nhiều nhất?',
  'Trạng thái thang máy hiện tại',
  'Cảnh báo nào cần ưu tiên xử lý?',
];

// ===== DEMO_LOGIN_REMOVE_BEFORE_JETSON_START =====
// Win11 local test only.
// Trước khi build Jetson Nano: đổi ENABLE_DEV_DEMO_LOGIN = false
// hoặc xóa toàn bộ block giữa START/END này.
const ENABLE_DEV_DEMO_LOGIN = true;

const DEV_DEMO_ACCOUNT = {
  employee_code: 'DEMO001',
  password: '123456',
  employee_id: 'DEMO001',
  full_name: 'Kỹ thuật viên Demo',
  employee_name: 'Kỹ thuật viên Demo',
  department: 'Trung tâm bảo trì',
  role: 'maintenance_demo',
  source: 'frontend_demo_win11',
};

function buildDemoSession() {
  return {
    employee_code: DEV_DEMO_ACCOUNT.employee_code,
    employee_id: DEV_DEMO_ACCOUNT.employee_id,
    full_name: DEV_DEMO_ACCOUNT.full_name,
    employee_name: DEV_DEMO_ACCOUNT.employee_name,
    department: DEV_DEMO_ACCOUNT.department,
    role: DEV_DEMO_ACCOUNT.role,
    source: DEV_DEMO_ACCOUNT.source,
    login_mode: 'demo_local',
    logged_in_at: new Date().toISOString(),
  };
}
// ===== DEMO_LOGIN_REMOVE_BEFORE_JETSON_END =====

const USER_STORAGE_KEY = 'maint_users_local_demo';
const TIMELINE_STORAGE_KEY = 'maintenance_local_timeline';

function formatEventType(event) {
  const raw = String(
    event.title || event.event_type || event.type || event.event || event.label || ''
  ).toUpperCase();
  if (raw.includes('BOTTLE')) return 'Phát hiện chai nhựa';
  if (raw.includes('FALL')) return 'Phát hiện té ngã';
  if (raw.includes('LYING')) return 'Phát hiện nằm bất thường';
  if (raw.includes('CROWD')) return 'Mật độ đông người';
  if (raw.includes('OVERLOAD')) return 'Quá tải';
  if (raw.includes('UNKNOWN') || raw.includes('UNIDENTIFIED')) return 'Đối tượng chưa gán nhãn';
  return event.title || event.event || event.event_type || 'Sự kiện camera';
}

function inferSeverity(event) {
  const raw = String(event.severity || event.type || event.event_type || '').toUpperCase();
  if (raw.includes('ERROR') || raw.includes('FALL') || raw.includes('OVERLOAD')) return 'error';
  if (raw.includes('WARN') || raw.includes('CROWD') || raw.includes('BOTTLE')) return 'warn';
  return 'info';
}

function formatClockLike(value) {
  if (!value) return '--';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

function formatFps(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  return num.toFixed(2);
}

function normalizeEventRow(event, idx) {
  return {
    id: event.id || event.event_id || idx,
    timestamp:
      event.event_ts || event.timestamp || event.created_at || event.time || new Date().toISOString(),
    time: formatClockLike(event.event_ts || event.timestamp || event.created_at || event.time),
    title: formatEventType(event),
    severity: inferSeverity(event),
    location: event.cam_id || event.location || '#A / Camera',
    peopleCount: event.people_count ?? event.people ?? '--',
    confidence:
      typeof event.confidence === 'number'
        ? `${Math.round(event.confidence * 100)}%`
        : event.confidence || '--',
    raw: event,
  };
}

function normalizeDensityData(data) {
  if (!Array.isArray(data) || !data.length) return [];
  return data.map((item, idx) => {
    const rawLabel = item.day || item.date || item.label || item.sample_ts || item.ts || '';
    let label = rawLabel;
    if (rawLabel) {
      const d = new Date(rawLabel);
      if (!Number.isNaN(d.getTime())) {
        label = d.toLocaleDateString('en-US', { weekday: 'short' });
      }
    }
    return {
      label: label || `D${idx + 1}`,
      value: Number(item.count ?? item.total ?? item.people_count ?? item.avg_people ?? item.value ?? 0),
    };
  });
}

function buildFallbackTableData(selectedDb, selectedTable, events, density, status, localUsers = []) {
  if (selectedDb === 'elevator_cv') {
    if (selectedTable === 'camera_events') {
      return {
        columns: ['id', 'event_ts', 'event_type', 'cam_id', 'people_count', 'confidence'],
        rows: events.map((event, idx) => ({
          id: event.id || idx + 1,
          event_ts: event.raw?.event_ts || event.raw?.timestamp || event.time,
          event_type: event.raw?.event_type || event.title,
          cam_id: event.raw?.cam_id || 'cam_01',
          people_count: event.peopleCount,
          confidence: event.confidence,
        })),
      };
    }
    if (selectedTable === 'camera_occupancy_samples') {
      return {
        columns: ['id', 'sample_day', 'people_count', 'cam_id'],
        rows: density.map((item, idx) => ({
          id: idx + 1,
          sample_day: item.label,
          people_count: item.value,
          cam_id: status?.cam_id || 'cam_01',
        })),
      };
    }
  }

  if (selectedDb === 'elevator_llm') {
    if (selectedTable === 'employees') {
      return {
        columns: ['employee_id', 'full_name', 'department'],
        rows: [
          { employee_id: 'NV001', full_name: 'Nguyễn Văn A', department: 'Kỹ thuật' },
          { employee_id: 'NV002', full_name: 'Trần Thị B', department: 'Quản lý' },
        ],
      };
    }
  }

  if (selectedDb === 'elevator_user') {
    return {
      columns: ['employee_code', 'full_name', 'department', 'role'],
      rows: localUsers.map((item) => ({
        employee_code: item.employee_code,
        full_name: item.full_name,
        department: item.department,
        role: item.role,
      })),
    };
  }

  return { columns: ['id'], rows: [] };
}

function getUnknownCandidate(events) {
  return events.find((event) =>
    /unknown|unidentified|chưa gán nhãn|unknown_person|unknown face/i.test(
      [event.raw?.event_type, event.raw?.title, event.raw?.event, event.title]
        .filter(Boolean)
        .join(' ')
    )
  );
}

function getColumnName(column) {
  if (typeof column === 'string') return column;
  return column?.column_name || column?.name || column?.key || '';
}

function readJsonLocalStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJsonLocalStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function exportRowsToCsv(filename, columns, rows) {
  const safeColumns = columns.map(getColumnName).filter(Boolean);
  const escapeCell = (value) => {
    const text = value == null ? '' : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  };
  const csv = [
    safeColumns.map(escapeCell).join(','),
    ...rows.map((row) => safeColumns.map((col) => escapeCell(row?.[col])).join(',')),
  ].join('\n');
  downloadTextFile(filename, csv, 'text/csv;charset=utf-8;');
}

function exportRowsToExcel(filename, columns, rows) {
  const safeColumns = columns.map(getColumnName).filter(Boolean);
  const headerHtml = safeColumns.map((col) => `<th>${col}</th>`).join('');
  const bodyHtml = rows
    .map((row) => {
      const cells = safeColumns
        .map((col) => `<td>${String(row?.[col] ?? '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</td>`)
        .join('');
      return `<tr>${cells}</tr>`;
    })
    .join('');
  const html = `
    <html>
      <head><meta charset="utf-8" /></head>
      <body>
        <table border="1">
          <thead><tr>${headerHtml}</tr></thead>
          <tbody>${bodyHtml}</tbody>
        </table>
      </body>
    </html>
  `;
  downloadTextFile(filename, html, 'application/vnd.ms-excel;charset=utf-8;');
}

function buildDeleteKeys(row, primaryKeys) {
  if (!primaryKeys?.length) {
    if (row?.id != null) return { id: row.id };
    return null;
  }
  const keys = {};
  for (const key of primaryKeys) {
    if (row?.[key] == null || row?.[key] === '') return null;
    keys[key] = row[key];
  }
  return keys;
}

function getRowId(row, index, primaryKeys) {
  if (row?._temp_id) return row._temp_id;
  const keys = buildDeleteKeys(row, primaryKeys);
  if (keys) return JSON.stringify(keys);
  if (row?.id != null) return `id:${row.id}`;
  return `row:${index}`;
}

function readLocalUsers() {
  return readJsonLocalStorage(USER_STORAGE_KEY, []);
}

function saveLocalUser(user) {
  const current = readLocalUsers();
  const withoutSame = current.filter((item) => item.employee_code !== user.employee_code);
  const next = [...withoutSame, user];
  saveJsonLocalStorage(USER_STORAGE_KEY, next);
  return next;
}

function readLocalTimeline() {
  return readJsonLocalStorage(TIMELINE_STORAGE_KEY, []);
}

function pushLocalTimeline(event) {
  const current = readLocalTimeline();
  const next = [
    {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: new Date().toISOString(),
      location: 'Trung tâm bảo trì',
      ...event,
    },
    ...current,
  ].slice(0, 100);
  saveJsonLocalStorage(TIMELINE_STORAGE_KEY, next);
  return next;
}

function LineDensityChart({ items }) {
  if (!items.length) {
    return <div className="empty-cell" style={{ padding: 24 }}>Chưa có dữ liệu mật độ/ngày.</div>;
  }

  const width = 720;
  const height = 220;
  const padding = 28;
  const maxValue = Math.max(1, ...items.map((item) => item.value));
  const stepX = items.length > 1 ? (width - padding * 2) / (items.length - 1) : 0;

  const points = items.map((item, index) => {
    const x = padding + index * stepX;
    const y = height - padding - (item.value / maxValue) * (height - padding * 2);
    return { x, y, ...item };
  });

  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
  const areaPath = `${path} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

  return (
    <div className="density-chart wide-density-chart" style={{ minHeight: 260 }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 240 }}>
        <defs>
          <linearGradient id="densityArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(43,210,182,0.35)" />
            <stop offset="100%" stopColor="rgba(43,210,182,0.02)" />
          </linearGradient>
        </defs>

        {[0, 1, 2, 3, 4].map((tick) => {
          const y = padding + ((height - padding * 2) / 4) * tick;
          return (
            <line
              key={tick}
              x1={padding}
              y1={y}
              x2={width - padding}
              y2={y}
              stroke="rgba(255,255,255,0.08)"
              strokeDasharray="4 6"
            />
          );
        })}

        <path d={areaPath} fill="url(#densityArea)" />
        <path d={path} fill="none" stroke="rgba(43,210,182,1)" strokeWidth="3" />

        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="4" fill="#2bd2b6" />
            <text x={point.x} y={point.y - 10} textAnchor="middle" fill="#eef6ff" fontSize="11">
              {point.value}
            </text>
            <text x={point.x} y={height - 8} textAnchor="middle" fill="#9cb1d1" fontSize="11">
              {point.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function Maintenance() {
  const showToast = useToast();
  const status = useElevatorStatus();
  const clock = useClock();

  const [authed, setAuthed] = useState(false);
  const [empCode, setEmpCode] = useState('');
  const [mssv, setMssv] = useState('');
  const [authMode, setAuthMode] = useState('login');
  const [registerForm, setRegisterForm] = useState({
    employee_code: '',
    password: '',
    full_name: '',
    department: 'Kỹ thuật',
    role: 'technician',
  });

  const [cameraVisible, setCameraVisible] = useState(true);
  const [streamUrl, setStreamUrl] = useState('');
  const [cvStatus, setCvStatus] = useState(null);
  const [cvEvents, setCvEvents] = useState([]);
  const [densityData, setDensityData] = useState([]);
  const [showFaceModal, setShowFaceModal] = useState(false);
  const [registerBusy, setRegisterBusy] = useState(false);
  const [faceForm, setFaceForm] = useState({
    employee_code: '',
    employee_name: '',
    department: '',
    note: '',
  });

  const [llmInput, setLlmInput] = useState('');
  const [llmOutput, setLlmOutput] = useState('Kết quả sẽ hiển thị ở đây.');
  const [llmBusy, setLlmBusy] = useState(false);
  const [llmAgentData, setLlmAgentData] = useState(null);
  const [agentSessionId, setAgentSessionId] = useState(() => getAgentSessionId());

  const [selectedDb, setSelectedDb] = useState('elevator_cv');
  const [selectedTable, setSelectedTable] = useState('camera_events');
  const [tableOptions, setTableOptions] = useState(() =>
    Object.fromEntries(
      Object.entries(DATASET_OPTIONS).map(([key, value]) => [key, value.map((item) => item.key)])
    )
  );
  const [selectedRowIds, setSelectedRowIds] = useState([]);
  const [expandedPanel, setExpandedPanel] = useState(null);
  const [selectedFloor, setSelectedFloor] = useState(5);

  const [lockedFloors, setLockedFloors] = useState(() => {
    const saved = localStorage.getItem('locked_floors');
    return saved ? JSON.parse(saved) : [5, 6, 7];
  });
  const [floorPins, setFloorPins] = useState(() => readJsonLocalStorage('floor_pins', {}));
  const [floorAuthConfig, setFloorAuthConfig] = useState(() => {
    const current = readJsonLocalStorage('floor_auth_config', {});
    return Object.fromEntries(
      Object.entries(current).map(([key, value]) => [
        key,
        {
          pin: value?.pin ?? true,
          qr: value?.qr ?? value?.face ?? false,
        },
      ])
    );
  });
  const [floorQrRules, setFloorQrRules] = useState(() => readJsonLocalStorage('floor_qr_rules', {}));
  const [editingPin, setEditingPin] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [qrEmployees, setQrEmployees] = useState('');
  const [qrTokens, setQrTokens] = useState('');

  const [tableColumns, setTableColumns] = useState([]);
  const [tableRows, setTableRows] = useState([]);
  const [primaryKeys, setPrimaryKeys] = useState([]);
  const [dataReadOnly, setDataReadOnly] = useState(false);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataConnected, setDataConnected] = useState(false);
  const [localUsers, setLocalUsers] = useState(() => readLocalUsers());
  const [localTimeline, setLocalTimeline] = useState(() => readLocalTimeline());

  useEffect(() => {
    setAuthed(false);
    setEmpCode('');
    setMssv('');
  }, []);

  useEffect(() => {
    let disposed = false;

    async function loadCvData() {
      try {
        const [streamData, statusData, eventsData, densityApiData] = await Promise.all([
          api.cvStreamUrl?.(),
          api.cvStatus?.(),
          api.cvEvents?.(20),
          api.cvDensity?.(7),
        ]);

        if (disposed) return;

        setStreamUrl(streamData?.stream_url || streamData?.url || '');
        setCvStatus(statusData || null);

        const eventsPayload = Array.isArray(eventsData)
          ? eventsData
          : eventsData?.events || eventsData?.items || [];
        setCvEvents(eventsPayload.map(normalizeEventRow));

        const densityPayload = Array.isArray(densityApiData)
          ? densityApiData
          : densityApiData?.items || densityApiData?.data || densityApiData?.density || [];
        setDensityData(normalizeDensityData(densityPayload));
      } catch {
        if (!disposed) {
          setCvStatus((prev) => prev || { camera_online: false, backend: 'TensorRT', cam_id: 'cam_01' });
          setCvEvents([]);
          setDensityData([]);
        }
      }
    }

    loadCvData();
    const timer = setInterval(loadCvData, 3000);
    return () => {
      disposed = true;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const tables = tableOptions[selectedDb] || [];
    if (!tables.includes(selectedTable)) {
      setSelectedTable(tables[0] || '');
    }
    setSelectedRowIds([]);
  }, [selectedDb, tableOptions, selectedTable]);

  useEffect(() => {
    let disposed = false;

    async function loadTableOptions() {
      if (!api.dataTables) return;
      try {
        const payload = await api.dataTables(selectedDb);
        if (disposed) return;
        const items = Array.isArray(payload?.items) ? payload.items : [];
        const next = items.map((item) => item?.name || item?.table_name).filter(Boolean);
        if (next.length) {
          setTableOptions((prev) => ({ ...prev, [selectedDb]: next }));
        }
      } catch {
        // fallback to local defaults
      }
    }

    loadTableOptions();
    return () => {
      disposed = true;
    };
  }, [selectedDb]);

  useEffect(() => {
    let disposed = false;

    async function loadTableData() {
      if (!selectedTable) return;

      if (selectedDb === 'elevator_user' && !api.dataTable) {
        const fallback = buildFallbackTableData(selectedDb, selectedTable, cvEvents, densityData, cvStatus, localUsers);
        if (!disposed) {
          setTableColumns(fallback.columns);
          setTableRows(fallback.rows);
          setPrimaryKeys(['employee_code']);
          setDataReadOnly(false);
          setDataConnected(false);
        }
        return;
      }

      if (!api.dataTable) {
        const fallback = buildFallbackTableData(selectedDb, selectedTable, cvEvents, densityData, cvStatus, localUsers);
        if (!disposed) {
          setTableColumns(fallback.columns);
          setTableRows(fallback.rows);
          setPrimaryKeys(fallback.columns.includes('id') ? ['id'] : []);
          setDataReadOnly(selectedDb === 'elevator_cv');
          setDataConnected(false);
        }
        return;
      }

      setDataLoading(true);
      try {
        const payload = await api.dataTable(selectedDb, selectedTable, 100, 0);
        if (disposed) return;
        const cols = Array.isArray(payload?.columns) ? payload.columns : [];
        const rows = Array.isArray(payload?.rows) ? payload.rows : [];
        setTableColumns(cols);
        setTableRows(rows);
        setPrimaryKeys(Array.isArray(payload?.primary_keys) ? payload.primary_keys : []);
        setDataReadOnly(Boolean(payload?.read_only));
        setDataConnected(true);
      } catch {
        const fallback = buildFallbackTableData(selectedDb, selectedTable, cvEvents, densityData, cvStatus, localUsers);
        if (!disposed) {
          setTableColumns(fallback.columns);
          setTableRows(fallback.rows);
          setPrimaryKeys(
            fallback.columns.includes('id') ? ['id'] : selectedDb === 'elevator_user' ? ['employee_code'] : []
          );
          setDataReadOnly(selectedDb === 'elevator_cv');
          setDataConnected(false);
        }
      } finally {
        if (!disposed) setDataLoading(false);
      }
    }

    loadTableData();
    return () => {
      disposed = true;
    };
  }, [selectedDb, selectedTable, cvEvents, densityData, cvStatus, localUsers]);

  useEffect(() => {
    const currentRule = floorQrRules[selectedFloor] || { employees: [], tokens: [] };
    setQrEmployees((currentRule.employees || []).join('\n'));
    setQrTokens((currentRule.tokens || []).join('\n'));
  }, [selectedFloor, floorQrRules]);

  const unknownCandidate = useMemo(() => getUnknownCandidate(cvEvents), [cvEvents]);

  const currentFloorCfg = floorAuthConfig[selectedFloor] || { pin: true, qr: false };
  const isSelectedFloorLocked = lockedFloors.includes(selectedFloor);
  const directionText = status.direction || '--';

  const summaryTiles = [
    { label: 'Tầng', value: status.floor ?? '--' },
    { label: 'Hướng', value: directionText },
    { label: 'Cửa', value: status.door ?? '--' },
    { label: 'Người', value: status.people_count ?? '--' },
    { label: 'Cập nhật', value: clock },
  ];

  const healthTiles = [
    { label: 'Camera', value: cvStatus?.camera_online ? 'ON' : 'OFF', tone: cvStatus?.camera_online ? 'ok' : 'err' },
    { label: 'FPS', value: formatFps(cvStatus?.fps), tone: 'info' },
    { label: 'Người', value: cvStatus?.people_count ?? cvStatus?.people ?? '--', tone: 'info' },
    { label: 'Event', value: cvStatus?.last_event_type || cvStatus?.last_event || '--', tone: 'info' },
    { label: 'Backend', value: cvStatus?.backend || 'TensorRT', tone: 'info' },
    { label: 'Cam ID', value: cvStatus?.cam_id || 'cam_01', tone: 'info' },
    { label: 'DB CV', value: 'elevator_cv', tone: 'ok' },
    { label: 'DB LLM', value: 'elevator_llm', tone: 'ok' },
    { label: 'DB USER', value: 'elevator_user', tone: 'ok' },
    { label: 'Mạng', value: 'Ổn định', tone: 'ok' },
    { label: 'Chờ gán nhãn', value: unknownCandidate ? 'Có' : 'Không', tone: unknownCandidate ? 'warn' : 'ok' },
  ];

  const timelineRows = useMemo(() => {
    const cvTimeline = cvEvents.map((event) => ({
      id: `cv-${event.id}`,
      time: event.time,
      timestamp: event.timestamp,
      title: event.title,
      severity: event.severity,
      location: event.location,
      actor: 'CV',
    }));

    const customTimeline = localTimeline.map((item, index) => ({
      id: item.id || `local-${index}`,
      time: formatClockLike(item.timestamp),
      timestamp: item.timestamp,
      title: item.title,
      severity: item.severity || 'info',
      location: item.location || 'Trung tâm bảo trì',
      actor: item.actor || 'SYS',
    }));

    return [...customTimeline, ...cvTimeline]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 30);
  }, [cvEvents, localTimeline]);

  const displayColumns = useMemo(() => tableColumns.map(getColumnName).filter(Boolean), [tableColumns]);

  const addLocalTimeline = (title, severity = 'info', actor = empCode || 'SYS', location = 'Trung tâm bảo trì') => {
    const next = pushLocalTimeline({ title, severity, actor, location });
    setLocalTimeline(next);
  };

  const handleLogin = async () => {
    if (!empCode.trim() || !mssv.trim()) {
      showToast('Vui lòng nhập mã nhân viên và mật khẩu');
      return;
    }

    if (
      ENABLE_DEV_DEMO_LOGIN &&
      empCode.trim() === DEV_DEMO_ACCOUNT.employee_code &&
      mssv === DEV_DEMO_ACCOUNT.password
    ) {
      localStorage.setItem('maint_authed', '1');
      localStorage.setItem('maint_emp_code', DEV_DEMO_ACCOUNT.employee_code);
      localStorage.setItem('maint_profile', JSON.stringify(buildDemoSession()));
      setAuthed(true);
      addLocalTimeline(`Đăng nhập demo local: ${DEV_DEMO_ACCOUNT.full_name}`, 'info', DEV_DEMO_ACCOUNT.employee_code);
      showToast('Đăng nhập demo thành công', 'Bạn đang ở chế độ test trên Win11.');
      return;
    }

    try {
      if (api.maintenanceLogin) {
        const payload = await api.maintenanceLogin({ employee_code: empCode.trim(), password: mssv });
        const profile = payload?.user || payload?.session || { employee_code: empCode.trim() };
        localStorage.setItem('maint_authed', '1');
        localStorage.setItem('maint_emp_code', empCode.trim());
        localStorage.setItem('maint_profile', JSON.stringify(profile));
        setAuthed(true);
        addLocalTimeline(`Đăng nhập: ${profile.full_name || profile.employee_code || empCode.trim()}`, 'info', empCode.trim());
        showToast('Đăng nhập thành công');
        return;
      }

      const users = readLocalUsers();
      const found = users.find((item) => item.employee_code === empCode.trim() && item.password === mssv);
      if (found) {
        localStorage.setItem('maint_authed', '1');
        localStorage.setItem('maint_emp_code', found.employee_code);
        localStorage.setItem('maint_profile', JSON.stringify(found));
        setAuthed(true);
        addLocalTimeline(`Đăng nhập local: ${found.full_name || found.employee_code}`, 'info', found.employee_code);
        showToast('Đăng nhập local thành công');
        return;
      }

      showToast('Đăng nhập thất bại', 'Sai tài khoản hoặc backend auth chưa bật.');
    } catch (error) {
      showToast('Đăng nhập thất bại', error?.message || 'Không thể đăng nhập');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('maint_authed');
    localStorage.removeItem('maint_emp_code');
    localStorage.removeItem('maint_profile');
    setAuthed(false);
    setEmpCode('');
    setMssv('');
  };

  const fillDemoCredentials = () => {
    setEmpCode(DEV_DEMO_ACCOUNT.employee_code);
    setMssv(DEV_DEMO_ACCOUNT.password);
  };

  const loginWithDemoAccount = () => {
    const session = buildDemoSession();
    localStorage.setItem('maint_authed', '1');
    localStorage.setItem('maint_emp_code', session.employee_code);
    localStorage.setItem('maint_profile', JSON.stringify(session));
    setEmpCode(session.employee_code);
    setAuthed(true);
    addLocalTimeline(`Đăng nhập demo local: ${session.full_name}`, 'info', session.employee_code);
    showToast('Đăng nhập demo thành công', 'Bạn đang ở chế độ test trên Win11.');
  };

  const handleRegister = async () => {
    if (!registerForm.employee_code.trim() || !registerForm.password.trim() || !registerForm.full_name.trim()) {
      showToast('Thiếu thông tin', 'Nhập mã nhân viên, họ tên và mật khẩu.');
      return;
    }

    try {
      if (api.maintenanceRegister) {
        await api.maintenanceRegister(registerForm);
        showToast('Đăng ký thành công');
      } else {
        const nextUsers = saveLocalUser({
          ...registerForm,
          employee_code: registerForm.employee_code.trim(),
          full_name: registerForm.full_name.trim(),
          department: registerForm.department.trim(),
        });
        setLocalUsers(nextUsers);
        showToast('Đăng ký local thành công', 'Dùng để test trên Win11.');
      }
      setAuthMode('login');
      setEmpCode(registerForm.employee_code.trim());
      setMssv(registerForm.password);
      addLocalTimeline(`Tạo tài khoản kỹ thuật: ${registerForm.employee_code.trim()}`, 'info', registerForm.employee_code.trim());
    } catch (error) {
      showToast('Đăng ký thất bại', error?.message || 'Không thể đăng ký');
    }
  };

  const handleResetAgentSession = () => {
    const next = resetAgentSessionId();
    setAgentSessionId(next);
    setLlmAgentData(null);
    setLlmOutput('Đã tạo phiên kỹ thuật mới cho LLM Console.');
    showToast('Đã tạo phiên debug mới');
  };

  const runLLMQuery = async () => {
    if (!llmInput.trim()) {
      setLlmOutput('Nhập câu hỏi để truy vấn.');
      return;
    }
    setLlmBusy(true);
    setLlmOutput('Đang truy vấn agent...');
    try {
      const data = await api.chat(llmInput, {
        session_id: agentSessionId,
        employee_id: empCode,
        employee_name: empCode,
      });
      setLlmOutput(data.answer || 'Không có phản hồi.');
      setLlmAgentData(data);
      setAgentSessionId(data.session_id || agentSessionId);
      if (data.requires_human) showToast('Agent đề xuất chuyển ca hoặc escalate kỹ thuật.');
    } catch (err) {
      setLlmOutput(`Lỗi truy vấn agent: ${err.message || err}`);
      setLlmAgentData(null);
    } finally {
      setLlmBusy(false);
    }
  };

  const persistLockedFloors = (next) => {
    setLockedFloors(next);
    localStorage.setItem('locked_floors', JSON.stringify(next));
  };

  const persistFloorPins = (next) => {
    setFloorPins(next);
    saveJsonLocalStorage('floor_pins', next);
  };

  const persistFloorAuthConfig = (next) => {
    setFloorAuthConfig(next);
    saveJsonLocalStorage('floor_auth_config', next);
  };

  const persistFloorQrRules = (next) => {
    setFloorQrRules(next);
    saveJsonLocalStorage('floor_qr_rules', next);
  };

  const toggleFloorLock = (floor) => {
    setSelectedFloor(floor);
    const next = lockedFloors.includes(floor) ? lockedFloors.filter((f) => f !== floor) : [...lockedFloors, floor];
    persistLockedFloors(next);
    addLocalTimeline(next.includes(floor) ? `Đã khóa tầng ${floor}` : `Đã mở khóa tầng ${floor}`, next.includes(floor) ? 'warn' : 'info', empCode || 'SYS');
    showToast(next.includes(floor) ? `Đã khóa tầng ${floor}` : `Đã mở khóa tầng ${floor}`);
  };

  const toggleAuthType = (floor, type) => {
    const floorCfg = floorAuthConfig[floor] || { pin: true, qr: false };
    const newFloorCfg = { ...floorCfg, [type]: !floorCfg[type] };
    if (!newFloorCfg.pin && !newFloorCfg.qr) {
      showToast('Phải bật ít nhất một phương thức mở khóa');
      return;
    }
    const next = { ...floorAuthConfig, [floor]: newFloorCfg };
    persistFloorAuthConfig(next);
    addLocalTimeline(`Cập nhật xác thực tầng ${floor}`, 'info', empCode || 'SYS');
  };

  const savePin = () => {
    if (!/^\d{4}$/.test(pinInput)) {
      showToast('PIN phải đủ 4 chữ số');
      return;
    }
    const next = { ...floorPins, [selectedFloor]: pinInput };
    persistFloorPins(next);
    setEditingPin(false);
    setPinInput('');
    addLocalTimeline(`Đặt PIN cho tầng ${selectedFloor}`, 'info', empCode || 'SYS');
    showToast(`Đã đặt PIN cho tầng ${selectedFloor}`);
  };

  const removePin = () => {
    const next = { ...floorPins };
    delete next[selectedFloor];
    persistFloorPins(next);
    addLocalTimeline(`Xóa PIN tầng ${selectedFloor}`, 'warn', empCode || 'SYS');
    showToast(`Đã xóa PIN tầng ${selectedFloor}`);
  };

  const saveQrConfig = () => {
    const employees = qrEmployees.split('\n').map((item) => item.trim()).filter(Boolean);
    const tokens = qrTokens.split('\n').map((item) => item.trim()).filter(Boolean);

    const next = { ...floorQrRules, [selectedFloor]: { employees, tokens } };
    persistFloorQrRules(next);
    addLocalTimeline(`Lưu QR rule cho tầng ${selectedFloor}`, 'info', empCode || 'SYS');
    showToast(`Đã lưu cấu hình QR cho tầng ${selectedFloor}`);
  };

  const openRegisterFace = () => {
    if (unknownCandidate) {
      setFaceForm((prev) => ({
        ...prev,
        note: `Ứng viên từ event ${unknownCandidate.title} lúc ${unknownCandidate.time}`,
      }));
    }
    setShowFaceModal(true);
  };

  const handleRegisterFace = async () => {
    if (!faceForm.employee_code.trim() || !faceForm.employee_name.trim()) {
      showToast('Nhập mã nhân viên và họ tên trước khi đăng ký');
      return;
    }
    setRegisterBusy(true);
    try {
      await api.registerFace?.({ ...faceForm, cam_id: cvStatus?.cam_id || 'cam_01', source_event: unknownCandidate?.raw || null });
      showToast('Đã gửi đăng ký khuôn mặt');
      setShowFaceModal(false);
      setFaceForm({ employee_code: '', employee_name: '', department: '', note: '' });
    } catch (err) {
      showToast('Backend chưa lưu được đăng ký khuôn mặt', err.message || String(err));
    } finally {
      setRegisterBusy(false);
    }
  };

  const toggleDataRow = (rowId) => {
    setSelectedRowIds((prev) => (prev.includes(rowId) ? prev.filter((id) => id !== rowId) : [...prev, rowId]));
  };

  const handleCellChange = (rowId, column, value) => {
    setTableRows((prev) => prev.map((row, idx) => {
      const currentId = getRowId(row, idx, primaryKeys);
      if (currentId !== rowId) return row;
      return { ...row, [column]: value, _dirty: true };
    }));
  };

  const handleDataAction = async (action) => {
    if (action === 'load' || action === 'refresh') {
      setSelectedTable((prev) => prev);
      showToast('Đã refresh bảng', `${selectedDb}.${selectedTable}`);
      return;
    }

    if (action === 'add') {
      const newRow = displayColumns.reduce((acc, col) => ({ ...acc, [col]: '' }), { _temp_id: `new-${Date.now()}`, _dirty: true });
      setTableRows((prev) => [newRow, ...prev]);
      return;
    }

    if (action === 'save') {
      const dirtyRows = tableRows.filter((row, idx) => row._dirty || selectedRowIds.includes(getRowId(row, idx, primaryKeys)));
      if (!dirtyRows.length) {
        showToast('Chưa có dòng nào thay đổi');
        return;
      }

      if (selectedDb === 'elevator_user' && !api.saveDataRow) {
        const nextUsers = [...localUsers];
        dirtyRows.forEach((row) => {
          const cleanRow = { ...row };
          delete cleanRow._dirty;
          delete cleanRow._temp_id;
          const existingIdx = nextUsers.findIndex((item) => item.employee_code === cleanRow.employee_code);
          if (existingIdx >= 0) nextUsers[existingIdx] = { ...nextUsers[existingIdx], ...cleanRow };
          else nextUsers.push(cleanRow);
        });
        saveJsonLocalStorage(USER_STORAGE_KEY, nextUsers);
        setLocalUsers(nextUsers);
        setTableRows((prev) => prev.map((row) => ({ ...row, _dirty: false })));
        showToast('Đã lưu dữ liệu local elevator_user');
        return;
      }

      if (!api.saveDataRow) {
        showToast('Backend chưa hỗ trợ saveDataRow');
        return;
      }

      try {
        for (const row of dirtyRows) {
          const payload = { ...row };
          delete payload._dirty;
          delete payload._temp_id;
          await api.saveDataRow(selectedDb, selectedTable, payload);
        }
        setTableRows((prev) => prev.map((row) => ({ ...row, _dirty: false })));
        showToast('Đã lưu thay đổi vào database');
      } catch (error) {
        showToast('Lưu thất bại', error?.message || 'Không thể lưu dữ liệu');
      }
      return;
    }

    if (action === 'delete') {
      const rowsToDelete = tableRows.filter((row, idx) => selectedRowIds.includes(getRowId(row, idx, primaryKeys)));
      if (!rowsToDelete.length) {
        showToast('Chưa chọn dòng nào để xóa');
        return;
      }

      if (selectedDb === 'elevator_user' && !api.deleteDataRow) {
        const nextUsers = localUsers.filter((item) => !rowsToDelete.some((row) => row.employee_code === item.employee_code));
        saveJsonLocalStorage(USER_STORAGE_KEY, nextUsers);
        setLocalUsers(nextUsers);
        setTableRows((prev) => prev.filter((row, idx) => !selectedRowIds.includes(getRowId(row, idx, primaryKeys))));
        setSelectedRowIds([]);
        showToast('Đã xóa dữ liệu local elevator_user');
        return;
      }

      if (!api.deleteDataRow) {
        showToast('Backend chưa hỗ trợ deleteDataRow');
        return;
      }

      try {
        for (const row of rowsToDelete) {
          const keys = buildDeleteKeys(row, primaryKeys);
          if (!keys) throw new Error('Không tìm được khóa chính để xóa an toàn');
          await api.deleteDataRow(selectedDb, selectedTable, keys);
        }
        setTableRows((prev) => prev.filter((row, idx) => !selectedRowIds.includes(getRowId(row, idx, primaryKeys))));
        setSelectedRowIds([]);
        showToast('Đã xóa các dòng đã chọn');
      } catch (error) {
        showToast('Xóa thất bại', error?.message || 'Không thể xóa dữ liệu');
      }
    }
  };

  const handleExportCsv = () => {
    exportRowsToCsv(`${selectedDb}_${selectedTable}_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`, displayColumns, tableRows);
    showToast('Đã lưu file .csv');
  };

  const handleExportExcel = () => {
    exportRowsToExcel(`${selectedDb}_${selectedTable}_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.xls`, displayColumns, tableRows);
    showToast('Đã lưu file .excel');
  };

  const authCardStyle = {
    width: 'min(680px, calc(100vw - 32px))',
    margin: '24px auto 0',
    padding: '24px',
    borderRadius: 24,
    border: '1px solid rgba(122,167,255,0.18)',
    background: 'radial-gradient(circle at top right, rgba(76,201,240,0.12), transparent 30%), rgba(7,14,32,0.88)',
    boxShadow: '0 24px 80px rgba(0,0,0,0.32)',
  };

  const authTabsStyle = {
    display: 'inline-flex',
    gap: 8,
    padding: 4,
    borderRadius: 14,
    border: '1px solid rgba(122,167,255,0.14)',
    background: 'rgba(255,255,255,0.03)',
    marginBottom: 16,
    flexWrap: 'wrap',
  };

  const authModeButton = (active) => ({
    minWidth: 120,
    padding: '10px 16px',
    borderRadius: 10,
    border: active ? '1px solid rgba(76,201,240,0.38)' : '1px solid transparent',
    background: active ? 'rgba(76,201,240,0.14)' : 'transparent',
    color: '#eef6ff',
    fontWeight: 800,
    cursor: 'pointer',
  });

  const authGridStyle = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 14,
    marginBottom: 16,
  };

  const authLabelStyle = { display: 'grid', gap: 8 };
  const authSpanStyle = {
    fontSize: 12,
    fontWeight: 800,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    color: '#78c3ff',
  };

  const authInputStyle = {
    width: '100%',
    minHeight: 44,
    padding: '12px 14px',
    borderRadius: 14,
    border: '1px solid rgba(141,180,255,0.16)',
    background: 'rgba(255,255,255,0.05)',
    color: '#eef6ff',
    outline: 'none',
    boxSizing: 'border-box',
  };

  const authActionsStyle = {
    display: 'flex',
    gap: 10,
    flexWrap: 'wrap',
    alignItems: 'center',
    marginTop: 2,
  };

  const authNoteStyle = {
    marginTop: 16,
    padding: '12px 14px',
    borderRadius: 14,
    border: '1px solid rgba(122,167,255,0.12)',
    background: 'rgba(255,255,255,0.03)',
    color: '#b9c9e2',
    lineHeight: 1.5,
  };

  if (!authed) {
    return (
      <div className="maint-login-screen">
        <div className="page-title">
          <h1>Trung tâm bảo trì</h1>
          <div className="meta">Chỉ dành cho kỹ thuật</div>
        </div>

        <div style={authCardStyle}>
          <div className="maint-login-head" style={{ marginBottom: 10 }}>
            <div>
              <h3 style={{ margin: 0 }}>{authMode === 'login' ? 'Đăng nhập bảo trì' : 'Đăng ký kỹ thuật viên'}</h3>
              <div className="muted" style={{ marginTop: 8 }}>
                {authMode === 'login'
                  ? 'Nhập mã nhân viên và mật khẩu để truy cập dashboard kỹ thuật.'
                  : 'Tạo tài khoản test local trên Win11 hoặc nối backend auth thật sau.'}
              </div>
            </div>
            <span className="tag">Maintenance only</span>
          </div>

          <div style={authTabsStyle}>
            <button type="button" style={authModeButton(authMode === 'login')} onClick={() => setAuthMode('login')}>Đăng nhập</button>
            <button type="button" style={authModeButton(authMode === 'register')} onClick={() => setAuthMode('register')}>Đăng ký</button>
          </div>

          {authMode === 'login' ? (
            <>
              <div style={authGridStyle}>
                <label style={authLabelStyle}>
                  <span style={authSpanStyle}>Mã nhân viên</span>
                  <input value={empCode} onChange={(e) => setEmpCode(e.target.value)} placeholder="VD: NV001" style={authInputStyle} />
                </label>
                <label style={authLabelStyle}>
                  <span style={authSpanStyle}>Mật khẩu kỹ thuật</span>
                  <input value={mssv} onChange={(e) => setMssv(e.target.value)} type="password" placeholder="Nhập mật khẩu" style={authInputStyle} />
                </label>
              </div>

              <div style={authActionsStyle}>
                <button className="btn btn-primary" onClick={handleLogin}>Đăng nhập</button>
                {ENABLE_DEV_DEMO_LOGIN ? (
                  <>
                    <button className="btn btn-ghost" onClick={fillDemoCredentials}>Điền tài khoản demo</button>
                    <button className="btn btn-ghost" onClick={loginWithDemoAccount}>Vào bằng demo</button>
                  </>
                ) : null}
              </div>

              {ENABLE_DEV_DEMO_LOGIN ? (
                <div style={authNoteStyle}>
                  Demo local Win11: <b>{DEV_DEMO_ACCOUNT.employee_code}</b> / <b>{DEV_DEMO_ACCOUNT.password}</b>. Trước khi build Jetson Nano, tìm chuỗi <b>DEMO_LOGIN_REMOVE_BEFORE_JETSON</b> để tắt hoặc xóa block này.
                </div>
              ) : null}
            </>
          ) : (
            <>
              <div style={authGridStyle}>
                <label style={authLabelStyle}>
                  <span style={authSpanStyle}>Mã nhân viên</span>
                  <input value={registerForm.employee_code} onChange={(e) => setRegisterForm((prev) => ({ ...prev, employee_code: e.target.value }))} placeholder="VD: NV010" style={authInputStyle} />
                </label>
                <label style={authLabelStyle}>
                  <span style={authSpanStyle}>Họ tên</span>
                  <input value={registerForm.full_name} onChange={(e) => setRegisterForm((prev) => ({ ...prev, full_name: e.target.value }))} placeholder="Nhập họ tên kỹ thuật viên" style={authInputStyle} />
                </label>
                <label style={authLabelStyle}>
                  <span style={authSpanStyle}>Mật khẩu</span>
                  <input type="password" value={registerForm.password} onChange={(e) => setRegisterForm((prev) => ({ ...prev, password: e.target.value }))} placeholder="Nhập mật khẩu" style={authInputStyle} />
                </label>
                <label style={authLabelStyle}>
                  <span style={authSpanStyle}>Phòng ban</span>
                  <input value={registerForm.department} onChange={(e) => setRegisterForm((prev) => ({ ...prev, department: e.target.value }))} placeholder="VD: Trung tâm bảo trì" style={authInputStyle} />
                </label>
              </div>

              <div style={authActionsStyle}>
                <button className="btn btn-primary" onClick={handleRegister}>Tạo tài khoản</button>
                <button className="btn btn-ghost" onClick={() => setAuthMode('login')}>Quay lại đăng nhập</button>
              </div>

              <div style={authNoteStyle}>
                Bản Win11 có thể dùng đăng ký local để test giao diện. Khi backend <b>elevator_user</b> sẵn sàng, chỉ cần thay nhánh local bằng API auth thật.
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="maintenance-v5">
      <div className="page-title">
        <h1>Trung tâm bảo trì</h1>
        <div className="meta">Xin chào, {empCode || 'Kỹ thuật viên'} · {clock}</div>
      </div>

      <section className="maint-top-grid" style={{ alignItems: 'stretch' }}>
        <div className="card maint-camera-card" style={{ minHeight: 590 }}>
          <div className="maint-card-head">
            <div>
              <h3>Live Camera &amp; CV Monitor</h3>
              <div className="muted">Camera thật từ CV service. Ẩn màn hình chỉ tác động UI, backend vẫn nhận diện và ghi dữ liệu.</div>
            </div>
          </div>

          <div className="camera-meta-row">
            <span className="camera-live-dot">● LIVE</span>
            <span className="tag">Person tracking</span>
            <span className="tag">Object detection</span>
            <span className="tag">People: {cvStatus?.people_count ?? '--'}</span>
            <span className="tag">FPS: {formatFps(cvStatus?.fps)}</span>
          </div>

          <div className="camera-stage" style={{ minHeight: 480 }}>
            {cameraVisible && streamUrl ? (
              <img src={streamUrl} alt="CV stream" className="camera-image-fill" />
            ) : (
              <div className="camera-placeholder-full">
                <div className="camera-icon">🖥️</div>
                <div className="camera-placeholder-title">{cameraVisible ? 'Chưa có luồng camera từ backend CV' : 'Màn hình camera đang được ẩn'}</div>
                <div className="camera-subnote">{cameraVisible ? 'Kiểm tra stream URL hoặc proxy MJPEG của backend chính.' : 'Camera backend vẫn chạy để nhận diện và ghi dữ liệu.'}</div>
              </div>
            )}

            <div className="camera-floating-actions">
              <button className="btn btn-ghost btn-sm" onClick={() => setCameraVisible((v) => !v)}>
                {cameraVisible ? 'Ẩn màn hình camera' : 'Bật màn hình camera'}
              </button>
              <button className="btn btn-primary btn-sm" onClick={openRegisterFace}>Đăng ký khuôn mặt</button>
            </div>
          </div>
        </div>

        <div className="maint-side-rail-v3" style={{ minHeight: 590, height: '100%', gridTemplateRows: '1fr' }}>
          <div className="card compact-health-card" style={{ height: '100%' }}>
            <div className="panel-title-row">
              <h3>Sức khỏe camera &amp; cấu hình</h3>
              <span className="tag">CV + LLM + USER</span>
            </div>
            <div className="metric-health-grid" style={{ flex: 1, alignContent: 'start' }}>
              {healthTiles.map((item) => (
                <div key={item.label} className={`health-chip ${item.tone || ''}`}>
                  <span>{item.label}</span>
                  <b>{item.value}</b>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="maint-middle-grid" style={{ alignItems: 'stretch' }}>
        <div className="card timeline-card" style={{ minHeight: 430, maxHeight: 430 }}>
          <div className="panel-title-row">
            <h3>Timeline sự kiện camera &amp; kỹ thuật</h3>
            <span className="tag">{timelineRows.length} mục gần nhất</span>
          </div>
          <div className="table-shell" style={{ flex: 1, overflowY: 'auto', maxHeight: 340 }}>
            <table className="table timeline-table">
              <thead>
                <tr>
                  <th>Giờ</th>
                  <th>Sự kiện</th>
                  <th>Mức độ</th>
                  <th>Vị trí</th>
                  <th>Người</th>
                </tr>
              </thead>
              <tbody>
                {timelineRows.length ? timelineRows.map((event) => (
                  <tr key={event.id}>
                    <td>{event.time}</td>
                    <td>{event.title}</td>
                    <td><span className={`event-badge ${event.severity}`}>{event.severity === 'error' ? 'LỖI' : event.severity === 'warn' ? 'WARN' : 'INFO'}</span></td>
                    <td>{event.location}</td>
                    <td>{event.actor}</td>
                  </tr>
                )) : (
                  <tr><td colSpan="5" className="empty-cell">Chưa có sự kiện camera gần đây.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card llm-console-card" style={{ minHeight: 430, maxHeight: 430 }}>
          <div className="llm-console-head">
            <div>
              <h3>Trợ lý bảo trì (LLM Console)</h3>
              <div className="muted">Debug agent, truy vết tool, xem memory và citations cho kỹ thuật viên.</div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={handleResetAgentSession}>Phiên mới</button>
          </div>

          <div className="llm-console-meta">
            <div className="llm-meta-main">
              <span className="tag">Phiên hiện tại</span>
              <span className="llm-session mono">{agentSessionId}</span>
            </div>
            <div className="llm-meta-tags">
              {llmAgentData?.intent ? <span className="tag">Intent: {llmAgentData.intent}</span> : null}
              {llmAgentData?.requires_human ? <span className="tag llm-warn">Cần handoff</span> : null}
            </div>
          </div>

          <div className="llm-quick-grid">
            {QUICK_PROMPTS.map((prompt) => (
              <button key={prompt} className="quick-prompt-btn" onClick={() => setLlmInput(prompt)}>{prompt}</button>
            ))}
          </div>

          <div className="llm-output llm-answer-box">{llmOutput}</div>

          <div className="llm-console-input-row">
            <input
              value={llmInput}
              onChange={(e) => setLlmInput(e.target.value)}
              placeholder="VD: Lỗi nào nhiều nhất?"
              onKeyDown={(e) => e.key === 'Enter' && runLLMQuery()}
              style={{
                background: 'rgba(255,255,255,0.06)',
                color: '#eef6ff',
                border: '1px solid rgba(122,167,255,0.14)',
                borderRadius: 14,
                padding: '12px 14px',
              }}
            />
            <button className="btn btn-primary" onClick={runLLMQuery} disabled={llmBusy}>{llmBusy ? 'Đang chạy...' : 'Gửi'}</button>
          </div>

          {llmAgentData ? <AgentTracePanel data={llmAgentData} compact /> : null}
        </div>
      </section>

      <section className="card data-manager-wide-card">
        <div className="data-manager-head">
          <div>
            <h3>Quản lý dữ liệu &amp; Database</h3>
            <div className="muted">Hiển thị dữ liệu thật từ API nếu backend sẵn sàng. Fallback local cho Win11 test.</div>
          </div>
          <span className="tag">{dataConnected ? 'Realtime API' : 'Fallback local'}</span>
        </div>

        <div className="data-manager-wide-layout">
          <div className="db-left-rail">
            <div className="db-connect-card">
              <div className="db-conn-row"><span>Host</span><b>localhost</b></div>
              <div className="db-conn-row"><span>Port</span><b>5432</b></div>
              <div className="db-conn-row"><span>User</span><b>elevator_ai</b></div>
              <div className="db-conn-row"><span>Data</span><b>{dataConnected ? 'API thật' : 'Fallback local'}</b></div>
            </div>

            <div className="db-picker-group">
              <div className="db-picker-title">Databases</div>
              <div className="db-chip-row">
                {Object.keys(DATASET_OPTIONS).map((db) => (
                  <button key={db} className={`db-chip ${selectedDb === db ? 'active' : ''}`} onClick={() => setSelectedDb(db)}>{db}</button>
                ))}
              </div>
            </div>

            <div className="db-picker-group">
              <div className="db-picker-title">Tables</div>
              <div className="db-table-list">
                {(tableOptions[selectedDb] || []).map((table) => (
                  <button key={table} className={`db-table-item ${selectedTable === table ? 'active' : ''}`} onClick={() => setSelectedTable(table)}>{table}</button>
                ))}
              </div>
            </div>

            <button className="btn btn-primary" onClick={() => handleDataAction('load')}>Load / Refresh Table</button>
          </div>

          <div className="db-right-panel">
            <div className="db-right-top">
              <div>
                <div className="db-current-label">Bảng hiện tại</div>
                <div className="db-current-name">{selectedDb}.{selectedTable}</div>
              </div>
              <div className="db-action-row">
                <button className="btn btn-ghost btn-sm" onClick={() => handleDataAction('add')}>Add Row</button>
                <button className="btn btn-ghost btn-sm" onClick={() => handleDataAction('delete')}>Delete Selected</button>
                <button className="btn btn-primary btn-sm" onClick={() => handleDataAction('save')}>Save Changes</button>
                <button className="btn btn-ghost btn-sm" onClick={() => handleDataAction('refresh')}>Refresh</button>
                <button className="btn btn-ghost btn-sm" onClick={handleExportCsv}>Lưu .csv</button>
                <button className="btn btn-ghost btn-sm" onClick={handleExportExcel}>Lưu .excel</button>
              </div>
            </div>

            <div className="db-table-shell">
              <table className="table db-table">
                <thead>
                  <tr>
                    <th></th>
                    {displayColumns.map((col) => <th key={col}>{col}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {dataLoading ? (
                    <tr><td colSpan={displayColumns.length + 1} className="empty-cell">Đang tải dữ liệu...</td></tr>
                  ) : tableRows.length ? (
                    tableRows.map((row, idx) => {
                      const rowId = getRowId(row, idx, primaryKeys);
                      return (
                        <tr key={rowId}>
                          <td>
                            <input type="checkbox" checked={selectedRowIds.includes(rowId)} onChange={() => toggleDataRow(rowId)} />
                          </td>
                          {displayColumns.map((col) => (
                            <td key={`${rowId}-${col}`}>
                              {dataReadOnly ? row[col] ?? '--' : (
                                <input
                                  value={row[col] ?? ''}
                                  onChange={(e) => handleCellChange(rowId, col, e.target.value)}
                                  style={{
                                    width: '100%',
                                    minWidth: 110,
                                    background: 'rgba(255,255,255,0.04)',
                                    color: '#eef6ff',
                                    border: '1px solid rgba(122,167,255,0.14)',
                                    borderRadius: 10,
                                    padding: '8px 10px',
                                  }}
                                />
                              )}
                            </td>
                          ))}
                        </tr>
                      );
                    })
                  ) : (
                    <tr><td colSpan={displayColumns.length + 1} className="empty-cell">Không có dữ liệu.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="muted db-footer-note">
              {selectedDb === 'elevator_cv' ? 'Nếu backend giữ elevator_cv ở read-only thì UI sẽ chỉ xem, không ghi đè dữ liệu realtime.' : 'Bảng LLM/USER có thể lưu local hoặc API thật tùy backend sẵn sàng.'}
            </div>
          </div>
        </div>
      </section>

      <div className="maintenance-bottom-actions">
        <button className={`btn btn-ghost ${expandedPanel === 'density' ? 'active-inline-toggle' : ''}`} onClick={() => setExpandedPanel((prev) => (prev === 'density' ? null : 'density'))}>
          {expandedPanel === 'density' ? 'Ẩn mật độ người/ngày' : 'Mật độ người / ngày'}
        </button>
        <button className={`btn btn-ghost ${expandedPanel === 'locks' ? 'active-inline-toggle' : ''}`} onClick={() => setExpandedPanel((prev) => (prev === 'locks' ? null : 'locks'))}>
          {expandedPanel === 'locks' ? 'Ẩn quản lý khóa tầng' : 'Quản lý khóa tầng'}
        </button>
        <button className="btn btn-ghost" onClick={handleLogout}>Đăng xuất</button>
      </div>

      {expandedPanel === 'density' && (
        <section className="card expandable-bottom-card">
          <div className="expandable-head">
            <div>
              <h3>Mật độ người / ngày</h3>
              <div className="muted">Nguồn từ camera_occupancy_samples của CV service.</div>
            </div>
            <span className="tag">Cam: {cvStatus?.cam_id || 'cam_01'}</span>
          </div>
          <LineDensityChart items={densityData} />
          <div className="inline" style={{ marginTop: 10 }}>
            <span className="pill">Cam: {cvStatus?.cam_id || 'cam_01'}</span>
            <span className="pill">Dạng biểu đồ: Line chart trực quan</span>
          </div>
        </section>
      )}

      {expandedPanel === 'locks' && (
        <section className="card expandable-bottom-card">
          <div className="expandable-head">
            <div>
              <h3>Quản lý khóa tầng</h3>
              <div className="muted">Giữ đúng cấu trúc gốc, nhưng summary đã được chuyển xuống đi cùng quản lý tầng.</div>
            </div>
          </div>

          <div className="lock-manager-v2" style={{ gridTemplateColumns: '1.2fr 0.8fr' }}>
            <div>
              <div className="lock-floor-grid">
                {ALL_FLOORS.map((floor) => {
                  const locked = lockedFloors.includes(floor);
                  const selected = selectedFloor === floor;
                  return (
                    <button key={floor} className={`floor-lock-tile ${locked ? 'locked' : 'unlocked'} ${selected ? 'selected' : ''}`} onClick={() => setSelectedFloor(floor)}>
                      <span className="floor-lock-label">T{floor}</span>
                      <span className="floor-lock-state">{locked ? '🔒' : '🔓'}</span>
                    </button>
                  );
                })}
              </div>

              <div className="lock-details-card" style={{ marginTop: 14 }}>
                <div className="lock-details-head">
                  <h4>Tầng {selectedFloor}</h4>
                  <button className="btn btn-ghost btn-sm" onClick={() => toggleFloorLock(selectedFloor)}>{isSelectedFloorLocked ? 'Mở khóa tầng' : 'Khóa tầng'}</button>
                </div>
                <div className="lock-status-line">
                  <span className={`event-badge ${isSelectedFloorLocked ? 'warn' : 'info'}`}>{isSelectedFloorLocked ? 'Đang khóa' : 'Đang mở'}</span>
                </div>

                {isSelectedFloorLocked && (
                  <>
                    <div className="lock-auth-grid">
                      <label className="lock-check"><input type="checkbox" checked={currentFloorCfg.pin ?? true} onChange={() => toggleAuthType(selectedFloor, 'pin')} />PIN</label>
                      <label className="lock-check"><input type="checkbox" checked={currentFloorCfg.qr ?? false} onChange={() => toggleAuthType(selectedFloor, 'qr')} />QR code</label>
                    </div>

                    {(currentFloorCfg.pin ?? true) && (
                      <div className="lock-pin-box" style={{ marginBottom: 12 }}>
                        {editingPin ? (
                          <div className="lock-pin-edit-row">
                            <input className="pin-inp" value={pinInput} onChange={(e) => setPinInput(e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="4 số" maxLength={4} />
                            <button className="btn btn-primary btn-sm" onClick={savePin}>Lưu PIN</button>
                            <button className="btn btn-ghost btn-sm" onClick={() => { setEditingPin(false); setPinInput(''); }}>Hủy</button>
                          </div>
                        ) : (
                          <div className="lock-pin-display">
                            <div className="muted">PIN hiện tại</div>
                            <div className="lock-pin-value">{floorPins[selectedFloor] ? '****' : 'Chưa đặt PIN'}</div>
                            <div className="inline">
                              <button className="btn btn-ghost btn-sm" onClick={() => { setEditingPin(true); setPinInput(floorPins[selectedFloor] || ''); }}>{floorPins[selectedFloor] ? 'Sửa PIN' : 'Đặt PIN'}</button>
                              {floorPins[selectedFloor] ? <button className="btn btn-ghost btn-sm" onClick={removePin}>Xóa PIN</button> : null}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {(currentFloorCfg.qr ?? false) && (
                      <div className="lock-pin-box">
                        <div className="muted" style={{ marginBottom: 8 }}>Nhân viên được phép QR</div>
                        <textarea value={qrEmployees} onChange={(e) => setQrEmployees(e.target.value)} rows={4} placeholder={'Mỗi dòng một mã nhân viên\nVD:\nNV001\nNV002'} style={{ width: '100%', borderRadius: 12, padding: 12, background: 'rgba(255,255,255,0.04)', color: '#eef6ff', border: '1px solid rgba(122,167,255,0.14)', resize: 'vertical' }} />
                        <div className="muted" style={{ marginTop: 10, marginBottom: 8 }}>QR token được phép</div>
                        <textarea value={qrTokens} onChange={(e) => setQrTokens(e.target.value)} rows={4} placeholder={'Mỗi dòng một token QR\nVD:\nQR_FLOOR_05_NV001'} style={{ width: '100%', borderRadius: 12, padding: 12, background: 'rgba(255,255,255,0.04)', color: '#eef6ff', border: '1px solid rgba(122,167,255,0.14)', resize: 'vertical' }} />
                        <div style={{ marginTop: 10 }}><button className="btn btn-primary btn-sm" onClick={saveQrConfig}>Lưu cấu hình QR</button></div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="maint-side-rail-v3" style={{ minHeight: 'unset', gridTemplateRows: 'auto auto', gap: 14 }}>
              <div className="card compact-summary-card">
                <div className="panel-title-row">
                  <h3>Tóm tắt hệ thống</h3>
                  <span className="tag">Realtime</span>
                </div>
                <div className="metric-compact-grid">
                  {summaryTiles.map((item) => (
                    <div key={item.label} className="metric-card-small"><span>{item.label}</span><strong>{item.value}</strong></div>
                  ))}
                </div>
              </div>

              <div className="card compact-health-card">
                <div className="panel-title-row">
                  <h3>Cấu hình mở tầng</h3>
                  <span className="tag">PIN + QR</span>
                </div>
                <div className="metric-compact-grid">
                  <div className="metric-card-small"><span>Tầng đang chọn</span><strong>T{selectedFloor}</strong></div>
                  <div className="metric-card-small"><span>Trạng thái</span><strong>{isSelectedFloorLocked ? 'Đang khóa' : 'Đang mở'}</strong></div>
                  <div className="metric-card-small"><span>PIN</span><strong>{currentFloorCfg.pin ? 'Bật' : 'Tắt'}</strong></div>
                  <div className="metric-card-small"><span>QR code</span><strong>{currentFloorCfg.qr ? 'Bật' : 'Tắt'}</strong></div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {showFaceModal && (
        <div className="overlay-backdrop" onClick={() => setShowFaceModal(false)}>
          <div className="face-register-modal" onClick={(e) => e.stopPropagation()}>
            <div className="face-register-head">
              <div>
                <h3>Đăng ký khuôn mặt nhân viên</h3>
                <div className="muted">Dùng khi model phát hiện người nhưng chưa biết đó là ai.</div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowFaceModal(false)}>Đóng</button>
            </div>

            <div className="face-register-candidate">
              <div className="face-candidate-title">Đối tượng chờ gán nhãn</div>
              {unknownCandidate ? (
                <div className="face-candidate-box">
                  <span>{unknownCandidate.title}</span>
                  <span>{unknownCandidate.time}</span>
                  <span>{unknownCandidate.location}</span>
                </div>
              ) : (
                <div className="face-candidate-box empty">Chưa có unknown person gần đây. Bạn vẫn có thể đăng ký thủ công.</div>
              )}
            </div>

            <div className="face-form-grid">
              <label>
                <span>Mã nhân viên</span>
                <input value={faceForm.employee_code} onChange={(e) => setFaceForm((prev) => ({ ...prev, employee_code: e.target.value }))} placeholder="VD: NV009" />
              </label>
              <label>
                <span>Họ tên</span>
                <input value={faceForm.employee_name} onChange={(e) => setFaceForm((prev) => ({ ...prev, employee_name: e.target.value }))} placeholder="Nhập họ tên nhân viên" />
              </label>
              <label>
                <span>Phòng ban</span>
                <input value={faceForm.department} onChange={(e) => setFaceForm((prev) => ({ ...prev, department: e.target.value }))} placeholder="VD: Kỹ thuật / Bảo vệ" />
              </label>
              <label>
                <span>Ghi chú</span>
                <textarea value={faceForm.note} onChange={(e) => setFaceForm((prev) => ({ ...prev, note: e.target.value }))} placeholder="Ghi chú nhận dạng / ca trực / snapshot" rows={4} />
              </label>
            </div>

            <div className="face-register-actions">
              <button className="btn btn-ghost" onClick={() => setShowFaceModal(false)}>Hủy</button>
              <button className="btn btn-primary" onClick={handleRegisterFace} disabled={registerBusy}>{registerBusy ? 'Đang gửi...' : 'Lưu đăng ký'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
