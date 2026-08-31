import React, { useMemo, useState, useRef, useCallback } from 'react';
import BotOrb from '../components/BotOrb';
import AgentTracePanel from '../components/AgentTracePanel';
import { useToast } from '../components/Toast';
import { speak, cancelSpeech, voiceChatOnce } from '../services/speech';
import { fetchChatAbortable, getAgentSessionId, resetAgentSessionId } from '../services/api';
import './Assistant.css';

function parseLocalFloorIntent(text) {
  const floorMatch = text.match(/(?:tầng|lên|xuống|đến)\s*(\d+)/i);
  if (!floorMatch) return null;
  const floor = Number.parseInt(floorMatch[1], 10);
  return Number.isFinite(floor) && floor >= 1 && floor <= 15 ? floor : null;
}

export default function Assistant() {
  const showToast = useToast();
  const [messages, setMessages] = useState([
    {
      id: 'boot-message',
      who: 'bot',
      text: 'Xin chào, tôi là Sunybot Agent. Tôi có thể hỗ trợ gọi tầng, kiểm tra trạng thái, tra cứu tri thức và giải thích các thao tác kỹ thuật.',
      agent: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [botMode, setBotMode] = useState('idle');
  const [stateText, setStateText] = useState('Sẵn sàng giao tiếp.');
  const [sessionId, setSessionId] = useState(() => getAgentSessionId());
  const abortRef = useRef(null);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  const addMessage = useCallback((message) => {
    setMessages((prev) => [...prev, { id: `${Date.now()}-${Math.random()}`, ...message }]);
    setTimeout(scrollToBottom, 50);
  }, []);

  const syncLocalFloor = useCallback((text, agentData) => {
    const parsedFloor = parseLocalFloorIntent(text);
    if (parsedFloor) {
      try { localStorage.setItem('lift_target', String(parsedFloor)); } catch {}
      return;
    }

    const toolFloor = agentData?.tool_trace?.find((item) => item.tool_name === 'call_elevator')?.args?.target_floor;
    if (toolFloor) {
      try { localStorage.setItem('lift_target', String(toolFloor)); } catch {}
    }
  }, []);

  const doSend = useCallback(async (text) => {
    if (!text) return;

    if (abortRef.current) {
      try { abortRef.current.abort(); } catch {}
      abortRef.current = null;
    }

    addMessage({ who: 'user', text, agent: null });
    setInput('');
    setBusy(true);
    setBotMode('speaking');
    setStateText('Agent đang phân tích câu hỏi...');

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const data = await fetchChatAbortable(text, controller.signal, { session_id: sessionId });
      syncLocalFloor(text, data);
      addMessage({ who: 'bot', text: data.answer || '...', agent: data });
      setSessionId(data.session_id || sessionId);
      setStateText(`Đã trả lời · intent: ${data.intent || 'general'}`);
      if (data.requires_human) showToast('Agent khuyến nghị chuyển cho người hỗ trợ.');
      speak(data.answer || '');
    } catch (e) {
      if (e && (e.name === 'AbortError' || String(e).includes('AbortError'))) {
        setStateText('Đã hủy truy vấn.');
      } else {
        addMessage({ who: 'bot', text: 'Sunybot Agent hiện không thể trả lời. Vui lòng kiểm tra backend.', agent: null });
        setStateText('Lỗi kết nối agent.');
      }
    } finally {
      abortRef.current = null;
      setBusy(false);
      setBotMode('idle');
    }
  }, [addMessage, sessionId, showToast, syncLocalFloor]);

  const handleStop = () => {
    cancelSpeech();
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch {}
      abortRef.current = null;
    }
    setBusy(false);
    setBotMode('idle');
    setStateText('Đã hủy.');
  };

  const handleVoice = () => {
    setBotMode('listening');
    setStateText('Đang nghe câu hỏi...');
    voiceChatOnce(
      (text) => {
        setInput(text);
        doSend(text);
      },
      null,
      () => {
        setBotMode('idle');
        setStateText('Sẵn sàng giao tiếp.');
      }
    );
  };

  const handleNewSession = () => {
    const next = resetAgentSessionId();
    setSessionId(next);
    setMessages([
      {
        id: 'new-session',
        who: 'bot',
        text: 'Đã tạo phiên agent mới. Bạn có thể bắt đầu hội thoại mà không dùng lại ngữ cảnh cũ.',
        agent: null,
      },
    ]);
    setStateText('Phiên mới đã sẵn sàng.');
    showToast('Đã tạo session agent mới');
  };

  const quickChips = useMemo(() => [
    { label: 'Gọi tầng 7', text: 'Gọi tôi lên tầng 7' },
    { label: 'Tầng hiện tại', text: 'Thang đang ở tầng mấy?' },
    { label: 'Trạng thái cửa', text: 'Cửa đang mở hay đóng?' },
    { label: 'Kiểm tra tải', text: 'Tình trạng quá tải?' },
    { label: 'Hướng dẫn kẹt thang', text: 'Nếu bị kẹt trong thang máy thì phải làm gì?' },
  ], []);

  const lastAgent = [...messages].reverse().find((m) => m.who === 'bot' && m.agent)?.agent || null;

  return (
    <div>
      <div className="page-title">
        <h1>Trợ lý ảo</h1>
        <div className="meta">Chat bằng giọng nói hoặc bàn phím · Agent session <span className="mono session-inline">{sessionId}</span></div>
      </div>

      <div className="grid-2 assistant-grid">
        <div className="panel">
          <div className="chat-layout">
            <div className="chat-box">
              <div className="assistant-topbar">
                <div className="assistant-status-text">{stateText}</div>
                <button className="btn btn-ghost btn-xs-inline" onClick={handleNewSession}>Phiên mới</button>
              </div>

              <div className="chat-messages">
                {messages.map((m) => (
                  <div key={m.id} className={`message-card ${m.who}`}>
                    <div className={`bubble ${m.who}`}>{m.text}</div>
                    {m.who === 'bot' && m.agent ? <AgentTracePanel data={m.agent} /> : null}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <div className="chat-input">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSend(input.trim())}
                  placeholder="Nhập câu hỏi..."
                />
                {!busy ? (
                  <button className="btn btn-primary" onClick={() => doSend(input.trim())}>Gửi</button>
                ) : (
                  <button className="btn btn-stop" onClick={handleStop}>Dừng</button>
                )}
                <button className="btn btn-ghost" onClick={handleVoice}>Mic</button>
              </div>
            </div>

            <div className="card agent-side-card">
              <h3>Câu hỏi mẫu</h3>
              <div className="chips">
                {quickChips.map((c) => (
                  <div key={c.label} className="chip" onClick={() => doSend(c.text)}>{c.label}</div>
                ))}
              </div>

              <div className="assistant-side-block">
                <h4>Phiên hiện tại</h4>
                <div className="muted mono">{sessionId}</div>
              </div>

              {lastAgent ? (
                <div className="assistant-side-block">
                  <h4>Tóm tắt agent gần nhất</h4>
                  <div className="muted">Intent: <b>{lastAgent.intent || 'general'}</b></div>
                  <div className="muted">Tool used: <b>{lastAgent.tool_trace?.length || 0}</b></div>
                  <div className="muted">Citations: <b>{lastAgent.citations?.length || 0}</b></div>
                  {lastAgent.memory_summary ? <div className="assistant-memory-preview">{lastAgent.memory_summary}</div> : null}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="panel suny">
          <BotOrb mode={botMode} title="Sunybot Agent" stateText={stateText} />
        </div>
      </div>
    </div>
  );
}
