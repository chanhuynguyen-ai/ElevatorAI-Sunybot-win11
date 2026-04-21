import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { useToast } from '../components/Toast';
import api from '../services/api';
import {
  appendMaintenanceTimeline,
  getFloorAuthConfig,
  getFloorPins,
  getLockedFloors,
  isQrAuthorizedForFloor,
  parseQrPayload,
  setLockedFloors,
  subscribeAccessChange,
} from '../utils/elevatorAccess';
import './CallFloor.css';

const FLOORS = Array.from({ length: 15 }, (_, index) => index + 1);
const QR_REGION_ID = 'call-floor-qr-reader';

function readAccessState() {
  return {
    lockedFloors: getLockedFloors(),
    authConfig: getFloorAuthConfig(),
    floorPins: getFloorPins(),
  };
}

export default function CallFloor() {
  const showToast = useToast();
  const [selectedFloors, setSelectedFloors] = useState([]);
  const [pressed, setPressed] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authStep, setAuthStep] = useState('pin');
  const [authOptions, setAuthOptions] = useState({ pin: true, qr: false });
  const [targetFloor, setTargetFloor] = useState(null);
  const [pin, setPin] = useState('');
  const [pinError, setPinError] = useState('');
  const [qrValue, setQrValue] = useState('');
  const [qrError, setQrError] = useState('');
  const [qrScannerState, setQrScannerState] = useState('idle');
  const [accessState, setAccessState] = useState(readAccessState);
  const scannerRef = useRef(null);

  useEffect(() => {
    return subscribeAccessChange(() => setAccessState(readAccessState()));
  }, []);

  const lockedFloors = accessState.lockedFloors;
  const floorPins = accessState.floorPins;
  const authConfig = accessState.authConfig;

  const activeFloorAuth = useMemo(() => {
    if (!targetFloor) return { pin: true, qr: false };
    return authConfig[String(targetFloor)] || { pin: true, qr: false };
  }, [authConfig, targetFloor]);

  useEffect(() => {
    let cancelled = false;

    async function startQrScanner() {
      if (!showAuthModal || authStep !== 'qr') return;

      const region = document.getElementById(QR_REGION_ID);
      if (!region) return;

      try {
        setQrScannerState('starting');
        const scanner = new Html5Qrcode(QR_REGION_ID);
        scannerRef.current = scanner;
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (decodedText) => {
            if (cancelled) return;
            setQrValue(decodedText);
            setQrScannerState('scanned');
          },
          () => {}
        );
        if (!cancelled) {
          setQrScannerState('running');
        }
      } catch {
        if (!cancelled) {
          setQrScannerState('camera-unavailable');
        }
      }
    }

    startQrScanner();

    return () => {
      cancelled = true;
      const current = scannerRef.current;
      scannerRef.current = null;
      if (current) {
        current.stop().catch(() => {}).finally(() => current.clear().catch(() => {}));
      }
    };
  }, [authStep, showAuthModal]);

  const resetAuthState = () => {
    setPin('');
    setPinError('');
    setQrValue('');
    setQrError('');
    setQrScannerState('idle');
  };

  const closeAuthModal = () => {
    setShowAuthModal(false);
    setTargetFloor(null);
    resetAuthState();
  };

  const doCall = async (floor) => {
    setSelectedFloors((prev) => (prev.includes(floor) ? prev : [...prev, floor]));
    setPressed(floor);
    setTimeout(() => setPressed(null), 220);

    try {
      localStorage.setItem('lift_target', String(floor));
    } catch {}

    try {
      const response = await api.callFloor(floor);
      const message = response?.message || response?.status || `Đã gọi tầng ${floor}`;
      showToast(typeof message === 'string' ? message : `Đã gọi tầng ${floor}`);
      appendMaintenanceTimeline({
        title: `Gọi tầng ${floor}`,
        severity: 'info',
        source: 'call_screen',
        location: `Cabin / Tầng ${floor}`,
        extra: { floor, response },
      });
    } catch (error) {
      showToast('Không thể gọi tầng', error?.message || 'Kiểm tra backend điều khiển');
    }
  };

  const unlockFloorAndCall = async (floor, payload = {}) => {
    const nextLocked = lockedFloors.filter((item) => item !== floor);
    setLockedFloors(nextLocked);
    setAccessState(readAccessState());

    appendMaintenanceTimeline({
      title: `QR mở khóa tầng ${floor}`,
      severity: 'info',
      source: 'qr_access',
      location: `Cabin / Tầng ${floor}`,
      actor: payload.employee_name || payload.employee_id || payload.token || 'QR authorized',
      extra: payload,
    });

    showToast(`Mở khóa QR thành công: tầng ${floor}`);
    closeAuthModal();
    await doCall(floor);
  };

  const handleCall = (floor) => {
    if (lockedFloors.includes(floor)) {
      const config = authConfig[String(floor)] || { pin: true, qr: false };
      setTargetFloor(floor);
      setAuthOptions(config);
      if (config.pin && config.qr) setAuthStep('select');
      else if (config.qr) setAuthStep('qr');
      else setAuthStep('pin');
      resetAuthState();
      setShowAuthModal(true);
      return;
    }
    doCall(floor);
  };

  const handlePinSubmit = async () => {
    if (!targetFloor) return;
    if (pin.length !== 4) {
      setPinError('PIN phải đủ 4 chữ số');
      return;
    }
    const expected = floorPins[String(targetFloor)] || floorPins[targetFloor];
    if (!expected || pin !== String(expected)) {
      setPinError('PIN không đúng. Vui lòng thử lại.');
      return;
    }

    setLockedFloors(lockedFloors.filter((item) => item !== targetFloor));
    setAccessState(readAccessState());
    appendMaintenanceTimeline({
      title: `PIN mở khóa tầng ${targetFloor}`,
      severity: 'info',
      source: 'pin_access',
      location: `Cabin / Tầng ${targetFloor}`,
    });
    showToast(`Đã mở khóa tầng ${targetFloor}`);
    const floor = targetFloor;
    closeAuthModal();
    await doCall(floor);
  };

  const handleQrSubmit = async () => {
    if (!targetFloor) return;
    const payload = parseQrPayload(qrValue);
    if (!payload.raw) {
      setQrError('Chưa có dữ liệu QR để xác thực');
      return;
    }

    const authorized = isQrAuthorizedForFloor(targetFloor, payload);
    if (!authorized) {
      setQrError('QR không được cấp quyền mở tầng này');
      appendMaintenanceTimeline({
        title: `QR bị từ chối ở tầng ${targetFloor}`,
        severity: 'warn',
        source: 'qr_access',
        location: `Cabin / Tầng ${targetFloor}`,
        actor: payload.employee_name || payload.employee_id || payload.token || 'QR unknown',
        extra: payload,
      });
      showToast('QR không hợp lệ cho tầng này');
      return;
    }

    await unlockFloorAndCall(targetFloor, payload);
  };

  const handlePinDigit = (digit) => {
    setPinError('');
    setPin((prev) => (prev.length >= 4 ? prev : `${prev}${digit}`));
  };

  const handlePinBackspace = () => {
    setPinError('');
    setPin((prev) => prev.slice(0, -1));
  };

  return (
    <div>
      <div className="page-title">
        <h1>Màn hình gọi tầng</h1>
        <div className="meta">Đã thay Face ID bằng QR code để đồng bộ với trung tâm bảo trì</div>
      </div>

      <div className="panel">
        <div className="call-grid">
          {FLOORS.map((floor) => {
            const isLocked = lockedFloors.includes(floor);
            const isSelected = selectedFloors.includes(floor);
            const isPressed = pressed === floor;
            return (
              <button
                key={floor}
                className={[
                  'floor-btn',
                  isLocked ? 'locked' : '',
                  isSelected ? 'selected' : '',
                  isPressed ? 'pressing' : '',
                ].join(' ')}
                onClick={() => handleCall(floor)}
              >
                <span className="floor-num">{floor}</span>
                {isLocked ? <span className="lock-label">🔒 Khóa</span> : null}
                {isSelected && !isLocked ? <span className="selected-label">✓ Đã chọn</span> : null}
              </button>
            );
          })}
        </div>

        <div className="auth-panel">
          <div className="auth-card">
            <h3>🔑 Mở khóa bằng PIN</h3>
            <div className="muted">Áp dụng cho các tầng khóa được cấu hình PIN trong trung tâm bảo trì.</div>
          </div>
          <div className="auth-card">
            <h3>📷 Mở khóa bằng QR code</h3>
            <div className="muted">Camera sẽ quét QR. Chỉ QR được cấp quyền mới mở được tầng bị khóa.</div>
          </div>
        </div>
      </div>

      {showAuthModal ? (
        <div className="pin-overlay" onClick={closeAuthModal}>
          <div className="pin-modal qr-modal" onClick={(event) => event.stopPropagation()}>
            {authStep === 'select' ? (
              <>
                <h3>Chọn phương thức xác thực</h3>
                <div className="muted modal-subtitle">Tầng {targetFloor} đang bị khóa.</div>
                <div className="auth-select-grid">
                  <button className="btn btn-primary" onClick={() => setAuthStep('pin')}>
                    Dùng PIN
                  </button>
                  <button className="btn btn-primary" onClick={() => setAuthStep('qr')}>
                    Dùng QR code
                  </button>
                </div>
              </>
            ) : null}

            {authStep === 'pin' ? (
              <>
                <h3>Nhập PIN mở khóa</h3>
                <div className="muted modal-subtitle">Tầng {targetFloor} yêu cầu PIN 4 số.</div>
                <div className="pin-dots">
                  {[0, 1, 2, 3].map((index) => (
                    <div key={index} className={`pin-dot ${index < pin.length ? 'filled' : ''}`} />
                  ))}
                </div>
                {pinError ? <div className="pin-error">{pinError}</div> : null}
                <div className="pin-pad">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, null, 0, 'del'].map((digit, index) => (
                    <button
                      key={`${digit}-${index}`}
                      className={`pin-key ${digit === null ? 'empty' : ''} ${digit === 'del' ? 'del' : ''}`}
                      onClick={() => {
                        if (digit === null) return;
                        if (digit === 'del') handlePinBackspace();
                        else handlePinDigit(String(digit));
                      }}
                      disabled={digit === null}
                    >
                      {digit === 'del' ? '⌫' : digit}
                    </button>
                  ))}
                </div>
                <div className="pin-actions">
                  <button
                    className="btn btn-ghost"
                    onClick={() => {
                      if (authOptions.pin && authOptions.qr) setAuthStep('select');
                      else closeAuthModal();
                    }}
                  >
                    Quay lại
                  </button>
                  <button className="btn btn-primary" onClick={handlePinSubmit}>
                    Xác nhận
                  </button>
                </div>
              </>
            ) : null}

            {authStep === 'qr' ? (
              <>
                <h3>Quét QR code mở khóa</h3>
                <div className="muted modal-subtitle">
                  Tầng {targetFloor} chỉ mở khi QR thuộc danh sách được phép trong trung tâm bảo trì.
                </div>

                <div className="qr-reader-shell">
                  <div id={QR_REGION_ID} className="qr-reader" />
                </div>

                <div className="qr-status-row">
                  <span className={`qr-chip ${qrScannerState}`}>
                    {qrScannerState === 'running' && 'Camera đang quét QR'}
                    {qrScannerState === 'starting' && 'Đang khởi tạo camera'}
                    {qrScannerState === 'scanned' && 'Đã nhận dữ liệu QR'}
                    {qrScannerState === 'camera-unavailable' && 'Không mở được camera, hãy dán mã QR thủ công'}
                    {qrScannerState === 'idle' && 'Sẵn sàng quét'}
                  </span>
                </div>

                <label className="qr-input-box">
                  <span>Dữ liệu QR</span>
                  <textarea
                    rows={4}
                    value={qrValue}
                    onChange={(event) => {
                      setQrValue(event.target.value);
                      setQrError('');
                    }}
                    placeholder='Ví dụ: {"token":"QR-F5-ALLOWED","employee_id":"NV001","employee_name":"Nguyễn Văn A"}'
                  />
                </label>

                {qrError ? <div className="pin-error">{qrError}</div> : null}

                <div className="pin-actions">
                  <button
                    className="btn btn-ghost"
                    onClick={() => {
                      if (authOptions.pin && authOptions.qr) setAuthStep('select');
                      else closeAuthModal();
                    }}
                  >
                    Quay lại
                  </button>
                  <button className="btn btn-primary" onClick={handleQrSubmit}>
                    Xác thực QR
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
