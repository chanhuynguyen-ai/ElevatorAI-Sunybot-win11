// gui/web/static/js/data_manager.js
import { dom } from "./dom.js";
import { api } from "./api.js";

function toast(msg) {
  if (window.SunyUI?.showToast) {
    window.SunyUI.showToast(msg);
  } else {
    console.log(msg);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const state = {
  connectionId: "",
  currentDb: "",
  currentTable: "",
  pkCols: [],
  autoIncPk: false,
  columns: [],
  originalRows: [],
  initialized: false,
  loading: false,
  connected: false,
  dbReady: false,
  tableLoaded: false,
};

function setStatus(msg) {
  if (dom.mysqlGridStatus) {
    dom.mysqlGridStatus.textContent = msg;
  }
}

function setLoading(on) {
  state.loading = on;
  updateButtonStates();
}

function getConnectionPayload() {
  return {
    host: dom.mysqlHost?.value.trim() || "localhost",
    port: Number(dom.mysqlPort?.value || 3306),
    user: dom.mysqlUser?.value.trim() || "",
    password: dom.mysqlPassword?.value || "",
  };
}

function clearDbOptions() {
  if (!dom.mysqlDbSelect) return;
  dom.mysqlDbSelect.innerHTML = `<option value="">Chọn database</option>`;
}

function fillDbOptions(databases = []) {
  if (!dom.mysqlDbSelect) return;

  clearDbOptions();

  databases.forEach((db) => {
    const opt = document.createElement("option");
    opt.value = db;
    opt.textContent = db;
    dom.mysqlDbSelect.appendChild(opt);
  });
}

function resetGrid() {
  renderGrid([], [], [], false);
  state.columns = [];
  state.pkCols = [];
  state.autoIncPk = false;
  state.originalRows = [];
  state.tableLoaded = false;
  updateButtonStates();
}

function updateButtonStates() {
  const hasConnection = !!state.connectionId;
  const hasDb = !!state.currentDb;
  const hasTable = !!state.currentTable;
  const hasLoadedTable = !!state.tableLoaded;

  if (dom.mysqlConnectBtn) dom.mysqlConnectBtn.disabled = state.loading;

  if (dom.mysqlUseDbBtn) {
    dom.mysqlUseDbBtn.disabled = state.loading || !hasConnection || !dom.mysqlDbSelect?.value;
  }

  if (dom.mysqlLoadTableBtn) {
    dom.mysqlLoadTableBtn.disabled = state.loading || !hasConnection || !hasDb || !hasTable;
  }

  if (dom.mysqlAddRowBtn) dom.mysqlAddRowBtn.disabled = state.loading || !hasLoadedTable;
  if (dom.mysqlDeleteBtn) dom.mysqlDeleteBtn.disabled = state.loading || !hasLoadedTable;
  if (dom.mysqlSaveBtn) dom.mysqlSaveBtn.disabled = state.loading || !hasLoadedTable;
  if (dom.mysqlRefreshBtn) dom.mysqlRefreshBtn.disabled = state.loading || !hasLoadedTable;

  if (dom.mysqlDbSelect) {
    dom.mysqlDbSelect.disabled = state.loading || !hasConnection;
  }
}

function renderTableList(tables = []) {
  if (!dom.mysqlTableList) return;

  const oldSelected = state.currentTable;
  dom.mysqlTableList.innerHTML = "";

  if (!tables.length) {
    const empty = document.createElement("div");
    empty.className = "muted";
    empty.textContent = "Không có bảng nào.";
    dom.mysqlTableList.appendChild(empty);
    state.currentTable = "";
    updateButtonStates();
    return;
  }

  let selectedFound = false;

  tables.forEach((tableName) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "table-item";
    btn.dataset.table = tableName;
    btn.textContent = tableName;

    if (oldSelected && oldSelected === tableName) {
      btn.classList.add("active");
      selectedFound = true;
    }

    btn.addEventListener("click", async () => {
      state.currentTable = tableName;
      selectTableButton(tableName);
      updateButtonStates();
      await loadCurrentTable();
    });

    dom.mysqlTableList.appendChild(btn);
  });

  if (!selectedFound) {
    state.currentTable = tables[0];
    selectTableButton(state.currentTable);
  }

  updateButtonStates();
}

function selectTableButton(tableName) {
  const buttons = dom.mysqlTableList?.querySelectorAll(".table-item") || [];
  buttons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.table === tableName);
  });
}

function buildReadonlyCell(value) {
  return `<span class="readonly-cell">${escapeHtml(value)}</span>`;
}

function renderGrid(columns = [], rows = [], pkCols = [], autoIncPk = false) {
  if (!dom.mysqlGrid) return;

  state.columns = [...columns];
  state.pkCols = [...pkCols];
  state.autoIncPk = !!autoIncPk;
  state.originalRows = JSON.parse(JSON.stringify(rows || []));
  state.tableLoaded = columns.length > 0;
  updateButtonStates();

  const thead = document.createElement("thead");
  const headTr = document.createElement("tr");

  const selectTh = document.createElement("th");
  selectTh.style.width = "52px";
  selectTh.textContent = "Chọn";
  headTr.appendChild(selectTh);

  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col;
    headTr.appendChild(th);
  });
  thead.appendChild(headTr);

  const tbody = document.createElement("tbody");

  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.className = "empty-state-row";
    const td = document.createElement("td");
    td.colSpan = columns.length + 1;
    td.className = "muted";
    td.textContent = "Bảng hiện chưa có dữ liệu.";
    tr.appendChild(td);
    tbody.appendChild(tr);
  } else {
    rows.forEach((row) => {
      const tr = document.createElement("tr");

      const selectTd = document.createElement("td");
      selectTd.className = "row-select-cell";
      selectTd.innerHTML = `<input type="checkbox" class="row-check"/>`;
      tr.appendChild(selectTd);

      columns.forEach((col) => {
        const td = document.createElement("td");
        const value = row?.[col] ?? "";

        const isReadonlyPk =
          autoIncPk &&
          pkCols.length === 1 &&
          pkCols[0].toLowerCase() === "id" &&
          col === pkCols[0];

        if (isReadonlyPk) {
          td.innerHTML = buildReadonlyCell(value);
          td.dataset.readonly = "1";
        } else {
          td.setAttribute("contenteditable", "true");
          td.textContent = value;
        }

        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  }

  dom.mysqlGrid.innerHTML = "";
  dom.mysqlGrid.appendChild(thead);
  dom.mysqlGrid.appendChild(tbody);

  bindRowSelection();
}

function bindRowSelection() {
  const tbody = dom.mysqlGrid?.querySelector("tbody");
  if (!tbody) return;

  const rows = tbody.querySelectorAll("tr");
  rows.forEach((tr) => {
    const checkbox = tr.querySelector(".row-check");
    if (!checkbox) return;

    checkbox.addEventListener("change", () => {
      tr.classList.toggle("row-selected", checkbox.checked);
    });
  });
}

function collectRowsFromGrid() {
  const tbody = dom.mysqlGrid?.querySelector("tbody");
  if (!tbody) return [];

  const trs = Array.from(tbody.querySelectorAll("tr"));
  const realRows = trs.filter((tr) => !tr.classList.contains("empty-state-row"));

  return realRows.map((tr) => {
    const tds = Array.from(tr.querySelectorAll("td")).slice(1);
    const row = {};

    state.columns.forEach((col, idx) => {
      const td = tds[idx];
      if (!td) {
        row[col] = "";
        return;
      }

      row[col] = td.textContent.trim();
    });

    return row;
  });
}

function addEmptyRow() {
  if (!state.columns.length) {
    toast("Hãy load bảng trước.");
    return;
  }

  const currentRows = collectRowsFromGrid();
  const newRow = {};

  state.columns.forEach((col) => {
    newRow[col] = "";
  });

  currentRows.push(newRow);
  renderGrid(state.columns, currentRows, state.pkCols, state.autoIncPk);
  setStatus(`Đã thêm 1 dòng mới vào bảng "${state.currentTable}".`);
}

function deleteSelectedRows() {
  if (!state.columns.length) {
    toast("Hãy load bảng trước.");
    return;
  }

  const tbody = dom.mysqlGrid?.querySelector("tbody");
  if (!tbody) return;

  const trs = Array.from(tbody.querySelectorAll("tr")).filter(
    (tr) => !tr.classList.contains("empty-state-row")
  );

  const selectedRows = trs.filter((tr) => tr.querySelector(".row-check")?.checked);

  if (!selectedRows.length) {
    toast("Chưa chọn dòng nào để xóa.");
    return;
  }

  const ok = window.confirm(`Bạn có chắc muốn xóa ${selectedRows.length} dòng khỏi lưới?`);
  if (!ok) return;

  const remainRows = [];

  trs.forEach((tr) => {
    const checked = tr.querySelector(".row-check")?.checked;
    if (checked) return;

    const tds = Array.from(tr.querySelectorAll("td")).slice(1);
    const row = {};
    state.columns.forEach((col, idx) => {
      row[col] = (tds[idx]?.textContent || "").trim();
    });
    remainRows.push(row);
  });

  renderGrid(state.columns, remainRows, state.pkCols, state.autoIncPk);
  setStatus(`Đã xóa khỏi lưới ${selectedRows.length} dòng. Nhấn Save Changes để lưu xuống DB.`);
}

async function connectMySQL() {
  try {
    setLoading(true);
    setStatus("Đang kết nối MySQL...");

    const payload = getConnectionPayload();
    const data = await api.adminMysql.connect(payload);

    state.connectionId = data.connection_id || "";
    state.currentDb = "";
    state.currentTable = "";
    state.connected = true;
    state.dbReady = false;

    fillDbOptions(data.databases || []);
    renderTableList([]);
    resetGrid();

    setStatus("Kết nối MySQL thành công. Hãy chọn database.");
    toast("Đã kết nối MySQL và tải danh sách databases.");
  } catch (err) {
    state.connectionId = "";
    state.currentDb = "";
    state.currentTable = "";
    state.connected = false;
    state.dbReady = false;
    resetGrid();

    setStatus(`Lỗi kết nối: ${err.message}`);
    toast(`Connect thất bại: ${err.message}`);
  } finally {
    setLoading(false);
    updateButtonStates();
  }
}

async function useDatabase() {
  try {
    if (!state.connectionId) {
      toast("Hãy Connect trước.");
      return;
    }

    const database = dom.mysqlDbSelect?.value || "";
    if (!database) {
      toast("Hãy chọn database.");
      return;
    }

    setLoading(true);
    setStatus(`Đang sử dụng database "${database}"...`);

    const data = await api.adminMysql.useDb({
      connection_id: state.connectionId,
      database,
    });

    state.currentDb = data.database || database;
    state.dbReady = true;
    renderTableList(data.tables || []);
    resetGrid();

    setStatus(`Đang dùng database "${state.currentDb}". Click bảng để load dữ liệu.`);
    toast(`Đã chọn database: ${state.currentDb}`);
  } catch (err) {
    state.currentDb = "";
    state.dbReady = false;
    resetGrid();

    setStatus(`Use Database thất bại: ${err.message}`);
    toast(`Use Database thất bại: ${err.message}`);
  } finally {
    setLoading(false);
    updateButtonStates();
  }
}

async function loadCurrentTable() {
  try {
    if (!state.connectionId) {
      toast("Hãy Connect trước.");
      return;
    }
    if (!state.currentDb) {
      toast("Hãy Use Database trước.");
      return;
    }
    if (!state.currentTable) {
      toast("Hãy chọn bảng.");
      return;
    }

    setLoading(true);
    setStatus(`Đang tải bảng "${state.currentTable}"...`);

    const data = await api.adminMysql.table({
      connection_id: state.connectionId,
      database: state.currentDb,
      table: state.currentTable,
    });

    state.currentTable = data.table || state.currentTable;
    selectTableButton(state.currentTable);
    renderGrid(data.columns || [], data.rows || [], data.pk_cols || [], data.auto_inc_pk);

    setStatus(
      `Đã tải bảng "${state.currentTable}". PK: ${
        (data.pk_cols || []).join(", ") || "(none)"
      }`
    );
    toast(`Đã load bảng: ${state.currentTable}`);
  } catch (err) {
    resetGrid();
    setStatus(`Load Table thất bại: ${err.message}`);
    toast(`Load Table thất bại: ${err.message}`);
  } finally {
    setLoading(false);
    updateButtonStates();
  }
}

async function saveCurrentTable() {
  try {
    if (!state.connectionId || !state.currentDb || !state.currentTable) {
      toast("Hãy Connect + Use Database + Load Table trước.");
      return;
    }

    const rows = collectRowsFromGrid();
    const ok = window.confirm(
      `Bạn có chắc muốn lưu thay đổi xuống bảng "${state.currentTable}" không?`
    );
    if (!ok) return;

    setLoading(true);
    setStatus(`Đang lưu thay đổi bảng "${state.currentTable}"...`);

    const data = await api.adminMysql.saveTable({
      connection_id: state.connectionId,
      database: state.currentDb,
      table: state.currentTable,
      rows,
    });

    setStatus(
      `Đã lưu. DELETE: ${data.deleted} | INSERT: ${data.inserted} | UPDATE: ${data.updated}`
    );
    toast(
      `Lưu thành công. DELETE: ${data.deleted} | INSERT: ${data.inserted} | UPDATE: ${data.updated}`
    );

    await loadCurrentTable();
  } catch (err) {
    setStatus(`Save thất bại: ${err.message}`);
    toast(`Save thất bại: ${err.message}`);
  } finally {
    setLoading(false);
    updateButtonStates();
  }
}

async function refreshCurrentTable() {
  if (!state.currentTable) {
    toast("Chưa có bảng để refresh.");
    return;
  }
  await loadCurrentTable();
}

function bindEvents() {
  dom.mysqlConnectBtn?.addEventListener("click", connectMySQL);
  dom.mysqlUseDbBtn?.addEventListener("click", useDatabase);
  dom.mysqlLoadTableBtn?.addEventListener("click", loadCurrentTable);
  dom.mysqlAddRowBtn?.addEventListener("click", addEmptyRow);
  dom.mysqlDeleteBtn?.addEventListener("click", deleteSelectedRows);
  dom.mysqlSaveBtn?.addEventListener("click", saveCurrentTable);
  dom.mysqlRefreshBtn?.addEventListener("click", refreshCurrentTable);

  dom.mysqlDbSelect?.addEventListener("change", () => {
    updateButtonStates();
  });
}

export function initDataManager() {
  if (state.initialized) return;
  state.initialized = true;

  bindEvents();
  resetGrid();
  setStatus("MySQL Manager sẵn sàng. Hãy Connect để bắt đầu.");
  updateButtonStates();
}

export function getDataManagerState() {
  return { ...state };
}
