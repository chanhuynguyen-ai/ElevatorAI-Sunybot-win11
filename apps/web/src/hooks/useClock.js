import { useState, useEffect } from 'react';

export default function useClock() {
    const [time, setTime] = useState(formatTime());

    useEffect(() => {
        const id = setInterval(() => setTime(formatTime()), 1000);
        return () => clearInterval(id);
    }, []);

    return time;
}

function formatTime() {
    const d = new Date();
    return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}


