import React, { useMemo } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import Topbar from './components/Topbar';
import { ToastProvider } from './components/Toast';
import useClock from './hooks/useClock';
import useElevatorStatus from './hooks/useElevatorStatus';
import useWeather from './hooks/useWeather';
import Home from './pages/Home';
import CallFloor from './pages/CallFloor';
import Assistant from './pages/Assistant';
import SOS from './pages/SOS';
import Guide from './pages/Guide';
import Maintenance from './pages/Maintenance';
import './App.css';

const navItems = [
  { to: '/', label: 'Màn hình chính' },
  { to: '/call', label: 'Gọi tầng' },
  { to: '/assistant', label: 'Trợ lý ảo' },
  { to: '/sos', label: 'SOS' },
  { to: '/guide', label: 'Hướng dẫn' },
  { to: '/maintenance', label: 'Bảo trì' },
];

export default function App() {
  const clock = useClock();
  const status = useElevatorStatus();
  const weather = useWeather();

  const overloadThreshold = Number(import.meta.env.VITE_OVERLOAD_THRESHOLD || status.overload_threshold || 4);

  const overloadInfo = useMemo(() => {
    const people = Number(status.people_count);
    const active = Boolean(status.overload) || (Number.isFinite(people) && people >= overloadThreshold);
    return {
      active,
      people: Number.isFinite(people) ? people : status.people_count,
      threshold: overloadThreshold,
    };
  }, [status.overload, status.people_count, overloadThreshold]);

  return (
    <ToastProvider>
      {overloadInfo.active ? (
        <div className="global-overload-alert" role="alert" aria-live="assertive">
          <div className="global-overload-badge">OVERLOAD</div>
          <div className="global-overload-copy">
            <strong>Cabin đang quá tải</strong>
            <span>
              {overloadInfo.people} người • ngưỡng {overloadInfo.threshold} người
            </span>
          </div>
        </div>
      ) : null}

      <Topbar
        time={clock}
        peopleCount={status.people_count ?? '--'}
        weather={weather}
      />

      <div className="wrap">
        <nav className="app-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `nav-btn${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/call" element={<CallFloor />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/sos" element={<SOS />} />
          <Route path="/guide" element={<Guide />} />
          <Route path="/maintenance" element={<Maintenance />} />
        </Routes>
      </div>
    </ToastProvider>
  );
}