import * as XLSX from 'xlsx';

function getColumnName(column) {
  if (typeof column === 'string') return column;
  return column?.column_name || column?.name || column?.key || 'column';
}

function normalizeRows(columns, rows) {
  const names = (columns || []).map(getColumnName);
  return (rows || []).map((row) => {
    const output = {};
    names.forEach((name) => {
      const value = row?.[name];
      if (value === null || value === undefined) {
        output[name] = '';
      } else if (typeof value === 'object') {
        output[name] = JSON.stringify(value);
      } else {
        output[name] = value;
      }
    });
    return output;
  });
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function exportRowsToCsv({ filename, columns, rows }) {
  const names = (columns || []).map(getColumnName);
  const normalized = normalizeRows(columns, rows);
  const escapeCell = (value) => {
    const cell = String(value ?? '');
    if (/[",\n]/.test(cell)) {
      return `"${cell.replace(/"/g, '""')}"`;
    }
    return cell;
  };

  const lines = [names.join(',')];
  normalized.forEach((row) => {
    lines.push(names.map((name) => escapeCell(row[name])).join(','));
  });

  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(filename, blob);
}

export function exportRowsToExcel({ filename, sheetName = 'Data', columns, rows }) {
  const normalized = normalizeRows(columns, rows);
  const worksheet = XLSX.utils.json_to_sheet(normalized);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
  const output = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob([output], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  downloadBlob(filename, blob);
}
