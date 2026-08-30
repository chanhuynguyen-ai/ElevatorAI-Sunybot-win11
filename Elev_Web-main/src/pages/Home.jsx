import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useElevatorStatus from '../hooks/useElevatorStatus';
import BotOrb from '../components/BotOrb';
import useWeather from '../hooks/useWeather';
import api from '../services/api';
import { speak, startWakeWordListener } from '../services/speech';
import './Home.css';

function parseFloorIntent(text) {
  const floorMatch = text?.match(/(?:tầng|lên|xuống|đến)\s*(\d+)/i);
  if (!floorMatch) return null;
  const floor = parseInt(floorMatch[1], 10);
  return floor >= 1 && floor <= 15 ? floor : null;
}

export default function Home() {
  const status = useElevatorStatus();
  const weather = useWeather();
  const navigate = useNavigate();
  const [botMode, setBotMode] = useState('idle');
  const [stateText, setStateText] = useState('Đang chờ wake word…');
  const [lastAgent, setLastAgent] = useState(null);

  useEffect(() => {
    const cleanup = startWakeWordListener({
      onModeChange: setBotMode,
      onStateText: setStateText,
      onWakeOnly: () => setStateText('Đã kích hoạt. Hãy nói câu lệnh...'),
      onWakeCommand: async (text) => {
        setStateText(`Đang xử lý: ${text}`);
        setBotMode('speaking');
        try {
          const parsedFloor = parseFloorIntent(text);
          if (parsedFloor) {
            try {
              localStorage.setItem('lift_target', String(parsedFloor));
            } catch {}
          }
          const data = await api.chat(text);
          setLastAgent(data);
          const answer = data.answer || '...';
          setStateText(`Sunybot: ${answer}`);
          speak(answer);
        } catch {
          setStateText('Sunybot hiện không thể trả lời.');
        } finally {
          setBotMode('listening');
        }
      },
    });

    return cleanup;
  }, []);

  const directionText = (dir) => {
    if (dir === 'UP') return '↑ Lên';
    if (dir === 'DOWN') return '↓ Xuống';
    return 'Đứng';
  };

  const displayFloor = status.floor === 1 ? 'G' : status.floor;

  return (
    <div>
      <div className="page-title">
        <h1>Giao diện người dùng</h1>
        <div className="meta">Thang máy thông minh · Sunybot Assistant</div>
      </div>

      <div className="home-shell">
        <div className="home-left-stack">
          <div className="panel home-status-panel">
            <div className="home-status-header">
              <div>
                <div className="section-eyebrow">Trạng thái hiện tại</div>
                <h2>Thang máy #A</h2>
              </div>
              <button className="btn btn-primary" onClick={() => navigate('/call')}>
                Gọi tầng
              </button>
            </div>

            <div className="home-floor-hero">
              <div>
                <div className="label">Tầng hiện tại</div>
                <div className="home-floor-display">{displayFloor ?? '--'}</div>
              </div>
              <div className={`badge ${status.overload ? 'err' : 'ok'}`}>
                {status.overload ? 'QUÁ TẢI' : 'Bình thường'}
              </div>
            </div>

            <div className="home-metric-grid">
              <div className="home-metric-card">
                <span className="metric-k">Chiều đi</span>
                <span className="metric-v">{directionText(status.direction)}</span>
              </div>
              <div className="home-metric-card">
                <span className="metric-k">Cửa</span>
                <span className="metric-v">{status.door ?? '--'}</span>
              </div>
              <div className="home-metric-card">
                <span className="metric-k">Số người</span>
                <span className="metric-v">{status.people_count ?? '--'}</span>
              </div>
              <div className="home-metric-card">
                <span className="metric-k">Thời gian</span>
                <span className="metric-v">{status.time ?? '--:--:--'}</span>
              </div>
              <div className="home-metric-card">
                <span className="metric-k">Thời tiết</span>
                <span className="metric-v">{weather}</span>
              </div>
              <div className="home-metric-card home-metric-card-accent">
                <span className="metric-k">Điều khiển nhanh</span>
                <span className="metric-v">Wake word: hey sunybot</span>
              </div>
            </div>
          </div>

          <div className="panel home-guide-panel">
            <div className="section-eyebrow">Hướng dẫn nhanh</div>
            <div className="home-guide-grid">
              <div className="guide-tile">
                <b>1.</b>
                <span>Nói “hey sunybot” để kích hoạt trợ lý.</span>
              </div>
              <div className="guide-tile">
                <b>2.</b>
                <span>Ra lệnh gọi tầng hoặc hỏi thông tin thang máy.</span>
              </div>
              <div className="guide-tile">
                <b>3.</b>
                <span>Vào mục Bảo trì để theo dõi camera, CV và sự kiện kỹ thuật.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel suny home-assistant-panel">
          <div className="assistant-card-head">
            <div>
              <div className="section-eyebrow">Trợ lý người dùng</div>
              <h2>Sunybot</h2>
            </div>
          </div>

          <BotOrb mode={botMode} stateText={stateText} />

          <div className="inline assistant-mode-row">
            <button className="btn btn-ghost" onClick={() => setBotMode('idle')}>Bình thường</button>
            <button className="btn btn-ghost" onClick={() => setBotMode('listening')}>Đang nghe</button>
            <button className="btn btn-ghost" onClick={() => setBotMode('speaking')}>Đang trả lời</button>
          </div>

          {lastAgent ? (
            <div className="assistant-last-agent">
              <div className="muted">Intent: <b>{lastAgent.intent || 'general'}</b></div>
              <div className="muted">Tool used: <b>{lastAgent.tool_trace?.length || 0}</b></div>
              <div className="muted">
                Confidence:{' '}
                <b>{typeof lastAgent.confidence === 'number' ? `${Math.round(lastAgent.confidence * 100)}%` : '—'}</b>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
