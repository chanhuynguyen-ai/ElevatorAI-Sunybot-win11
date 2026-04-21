// gui/web/static/js/api.js

async function request(url, options = {}) {
  const finalOptions = {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  };

  const res = await fetch(url, finalOptions);

  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }

  if (!res.ok || data?.ok === false) {
    throw new Error(data?.error || `HTTP ${res.status}`);
  }

  return data;
}

function toQuery(params = {}) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") {
      usp.set(k, String(v));
    }
  });
  const s = usp.toString();
  return s ? `?${s}` : "";
}

function normalizeChatPayload(input, options = {}) {
  if (typeof input === "string") {
    return {
      message: input,
      question: input,
      session_id: options.sessionId || options.session_id || null,
      employee_id: options.employeeId || options.employee_id || "",
      employee_name: options.employeeName || options.employee_name || "",
    };
  }

  const payload = input || {};
  const message = payload.message || payload.question || "";

  return {
    message,
    question: payload.question || message,
    session_id: payload.session_id || payload.sessionId || null,
    employee_id: payload.employee_id || payload.employeeId || "",
    employee_name: payload.employee_name || payload.employeeName || "",
  };
}

export const api = {
  async elevatorStatus(elevatorId = 1) {
    return request(`/api/elevator/status${toQuery({ elevator_id: elevatorId })}`, {
      method: "GET",
    });
  },

  async agentStatus() {
    return request("/status", { method: "GET" });
  },

  async weather() {
    try {
      return await request("/api/weather", { method: "GET" });
    } catch (error) {
      return {
        ok: false,
        unavailable: true,
        error: error.message || "Weather endpoint unavailable",
      };
    }
  },

  async chat(input, options = {}) {
    const payload = normalizeChatPayload(input, options);
    return request("/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async command(payload = {}) {
    return request("/command", {
      method: "POST",
      body: JSON.stringify({
        elevator_id: payload.elevator_id ?? payload.elevatorId ?? 1,
        from_floor: payload.from_floor ?? payload.fromFloor ?? null,
        target_floor: payload.target_floor ?? payload.targetFloor ?? null,
        direction: payload.direction || "up",
      }),
    });
  },

  async sos(payload) {
    try {
      return await request("/api/sos", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      });
    } catch (error) {
      return {
        ok: false,
        unavailable: true,
        error: error.message || "SOS endpoint unavailable",
      };
    }
  },

  async callFloor(floor, options = {}) {
    const fromFloor =
      options.from_floor ?? options.fromFloor ?? options.currentFloor ?? null;
    const direction =
      options.direction ||
      (typeof fromFloor === "number" && typeof floor === "number"
        ? floor >= fromFloor
          ? "up"
          : "down"
        : "up");

    return this.command({
      elevator_id: options.elevator_id ?? options.elevatorId ?? 1,
      from_floor: fromFloor,
      target_floor: floor,
      direction,
    });
  },

  adminMysql: {
    async connect(payload) {
      return request("/api/admin/mysql/connect", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    async useDb(payload) {
      return request("/api/admin/mysql/use-db", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    async tables({ connection_id, database }) {
      return request(
        `/api/admin/mysql/tables${toQuery({ connection_id, database })}`,
        { method: "GET" }
      );
    },

    async table({ connection_id, database, table }) {
      return request(
        `/api/admin/mysql/table${toQuery({ connection_id, database, table })}`,
        { method: "GET" }
      );
    },

    async saveTable(payload) {
      return request("/api/admin/mysql/save-table", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
  },
};
