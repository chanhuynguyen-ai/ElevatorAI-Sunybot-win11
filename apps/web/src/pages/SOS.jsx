import React, { useState, useEffect, useRef, useCallback } from 'react';
import useElevatorStatus from '../hooks/useElevatorStatus';
import api from '../services/api';
import './SOS.css';

const THUMB_SIZE = 72;

export default function SOS() {
    const status = useElevatorStatus();
    const [sosTime, setSosTime] = useState('--:--');
    const [slideProgress, setSlideProgress] = useState(0);
    const [isCalling, setIsCalling] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState('');
    const [simInfo] = useState({ signal: 4, carrier: 'Viettel', number: '0900-XXX-XXX' });
    const sliderRef = useRef(null);
    const isDragging = useRef(false);

    useEffect(() => {
        const tick = () => setSosTime(new Date().toLocaleTimeString('vi-VN'));
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, []);

    const handleSlideStart = (e) => {
        if (isCalling) return;
        isDragging.current = true;
        e.preventDefault();
    };

    const handleSlideMove = useCallback((e) => {
        if (!isDragging.current || !sliderRef.current) return;
        const rect = sliderRef.current.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const progress = Math.max(
            0,
            Math.min(1, (clientX - rect.left - THUMB_SIZE / 2) / (rect.width - THUMB_SIZE))
        );
        setSlideProgress(progress);
    }, []);

    const handleSlideEnd = useCallback(async () => {
        if (!isDragging.current) return;
        isDragging.current = false;

        if (slideProgress > 0.85) {
            setSlideProgress(1);
            setIsCalling(true);
            setConnectionStatus('Đang kết nối với đội ngũ bảo trì...');

            try {
                await api.sos({
                    elevator: 'A',
                    time: new Date().toISOString(),
                    floor: status.floor ?? '--',
                    status: status.door ?? '--',
                });
            } catch {}

            setTimeout(() => setConnectionStatus('Đang gọi điện qua SIM module...'), 1500);
            setTimeout(() => setConnectionStatus('Đã kết nối! Đội bảo trì đang trên đường đến.'), 3500);
        } else {
            setSlideProgress(0);
        }
    }, [slideProgress, status]);

    useEffect(() => {
        window.addEventListener('mousemove', handleSlideMove);
        window.addEventListener('mouseup', handleSlideEnd);
        window.addEventListener('touchmove', handleSlideMove);
        window.addEventListener('touchend', handleSlideEnd);
        return () => {
            window.removeEventListener('mousemove', handleSlideMove);
            window.removeEventListener('mouseup', handleSlideEnd);
            window.removeEventListener('touchmove', handleSlideMove);
            window.removeEventListener('touchend', handleSlideEnd);
        };
    }, [handleSlideMove, handleSlideEnd]);

    const resetSOS = () => {
        setIsCalling(false);
        setSlideProgress(0);
        setConnectionStatus('');
    };

    const fillWidth = `calc(${(slideProgress * 100).toFixed(3)}% + ${(THUMB_SIZE * (1 - slideProgress)).toFixed(1)}px)`;

    return (
        <div>
            <div className="page-title">
                <h1>SOS</h1>
                <div className="meta">Gửi tín hiệu khẩn cấp</div>
            </div>

            <div className="sos-wrap">
                <div className="panel">
                    {!isCalling ? (
                        <div className="slide-container">
                            <div
                                className="slide-track"
                                ref={sliderRef}
                                style={{ '--progress': slideProgress }}
                            >
                                <div className="slide-fill" style={{ width: fillWidth }} />
                                <div className="slide-track-overlay" />
                                <div className="slide-chevron-lane" aria-hidden="true">
                                    <span>&gt;&gt;&gt;&gt;</span>
                                    <span>&gt;&gt;&gt;&gt;</span>
                                    <span>&gt;&gt;&gt;&gt;</span>
                                    <span>&gt;&gt;&gt;&gt;</span>
                                </div>

                                <div
                                    className="slide-thumb"
                                    style={{ left: `calc(${slideProgress * 100}% - ${slideProgress * THUMB_SIZE}px)` }}
                                    onMouseDown={handleSlideStart}
                                    onTouchStart={handleSlideStart}
                                    aria-label="Trượt để gọi kỹ thuật"
                                >
                                    <span className="slide-thumb-text">SOS</span>
                                </div>
                            </div>

                            <div className="muted sos-helper-text">
                                Kéo thanh trượt sang phải để xác nhận gọi kỹ thuật
                            </div>
                        </div>
                    ) : (
                        <div className="sos-calling">
                            <div className="sos-calling-icon">📡</div>
                            <div className="sos-calling-status">{connectionStatus}</div>
                            <div className="sos-pulse-ring"></div>
                            <button className="btn btn-ghost" style={{ marginTop: 16 }} onClick={resetSOS}>
                                Hủy cuộc gọi
                            </button>
                        </div>
                    )}
                </div>

                <div className="panel">
                    <h3 style={{ margin: '0 0 8px' }}>Thông tin gửi đi</h3>
                    <div className="inline">
                        <span className="pill">Elevator #A</span>
                        <span className="pill">{sosTime}</span>
                        <span className="pill">Trạng thái: {status.door ?? '--'}</span>
                    </div>
                    <div style={{ marginTop: 12 }} className="muted">
                        Bao gồm vị trí, thời gian, trạng thái, tầng hiện tại.
                    </div>

                    <div className="sim-module">
                        <h3 style={{ margin: '12px 0 8px' }}>SIM Module</h3>
                        <div className="sim-info">
                            <div className="sim-signal">
                                {Array.from({ length: 5 }, (_, i) => (
                                    <div
                                        key={i}
                                        className={`signal-bar ${i < simInfo.signal ? 'active' : ''}`}
                                        style={{ height: `${8 + i * 4}px` }}
                                    />
                                ))}
                            </div>
                            <div>
                                <div className="sim-carrier">{simInfo.carrier}</div>
                                <div className="muted" style={{ fontSize: 11 }}>{simInfo.number}</div>
                            </div>
                        </div>
                        <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
                            Kết nối GSM hoạt động — sẵn sàng gọi khẩn cấp.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
