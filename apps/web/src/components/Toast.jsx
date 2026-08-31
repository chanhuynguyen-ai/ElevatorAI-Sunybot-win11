import React, { createContext, useContext, useState, useCallback } from 'react';
import './Toast.css';

const ToastContext = createContext(null);

export function useToast() {
    return useContext(ToastContext);
}

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const showToast = useCallback((message, detail = '', ttlMs = 2200) => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, detail, visible: true }]);

        setTimeout(() => {
            setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, visible: false } : t)));
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, 220);
        }, Math.max(800, ttlMs));
    }, []);

    return (
        <ToastContext.Provider value={showToast}>
            {children}
            <div className="suny-toast-wrap">
                {toasts.map((t) => (
                    <div key={t.id} className={`suny-toast${t.visible ? ' show' : ''}`}>
                        <div className="t">{t.message}</div>
                        {t.detail && <div className="d">{t.detail}</div>}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
