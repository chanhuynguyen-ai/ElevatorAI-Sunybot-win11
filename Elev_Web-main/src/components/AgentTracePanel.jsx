import React from 'react';
import './AgentTracePanel.css';

function formatPercent(value) {
  if (typeof value !== 'number') return '—';
  return `${Math.round(value * 100)}%`;
}

function shortArgs(args = {}) {
  const entries = Object.entries(args).slice(0, 4);
  if (!entries.length) return 'Không có tham số';
  return entries.map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · ');
}

export default function AgentTracePanel({ data, compact = false }) {
  if (!data) return null;

  const {
    intent,
    confidence,
    source,
    session_id,
    tool_trace = [],
    citations = [],
    memory_summary,
    requires_human,
    status,
  } = data;

  return (
    <div className={`agent-trace-panel ${compact ? 'compact' : ''}`}>
      <div className="agent-trace-head">
        <span className="agent-pill primary">intent: {intent || 'general'}</span>
        <span className="agent-pill">confidence: {formatPercent(confidence)}</span>
        <span className="agent-pill">source: {source || 'agent'}</span>
        <span className="agent-pill">status: {status || 'ok'}</span>
      </div>

      <div className="agent-meta-row">
        <div><b>session</b>: <span className="mono">{session_id || '—'}</span></div>
        <div><b>handoff</b>: {requires_human ? 'Cần hỗ trợ người thật' : 'Chưa cần'}</div>
      </div>

      {tool_trace.length > 0 && (
        <div className="agent-section">
          <div className="agent-section-title">Tool trace</div>
          <div className="agent-tool-list">
            {tool_trace.map((tool) => (
              <div key={tool.id || `${tool.tool_name}-${tool.summary}`} className="agent-tool-item">
                <div className="agent-tool-head">
                  <span className="agent-tool-name">{tool.tool_name}</span>
                  <span className={`agent-tool-status ${tool.status || 'ok'}`}>{tool.status || 'ok'}</span>
                  <span className="agent-tool-time">{tool.duration_ms || 0} ms</span>
                </div>
                <div className="agent-tool-args">{shortArgs(tool.args)}</div>
                {tool.summary ? <div className="agent-tool-summary">{tool.summary}</div> : null}
              </div>
            ))}
          </div>
        </div>
      )}

      {citations.length > 0 && (
        <div className="agent-section">
          <div className="agent-section-title">Citations</div>
          <div className="agent-citation-list">
            {citations.map((citation) => (
              <div key={citation.id || `${citation.source}-${citation.content}`} className="agent-citation-item">
                <div className="agent-citation-source">{citation.source}</div>
                {citation.content ? <div className="agent-citation-text">{citation.content}</div> : null}
                {typeof citation.score === 'number' ? (
                  <div className="agent-citation-score">score: {citation.score.toFixed(3)}</div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}

      {memory_summary ? (
        <div className="agent-section">
          <div className="agent-section-title">Memory summary</div>
          <div className="agent-memory-box">{memory_summary}</div>
        </div>
      ) : null}
    </div>
  );
}
