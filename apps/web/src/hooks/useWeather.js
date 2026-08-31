import { useState, useEffect } from 'react';

export default function useWeather(intervalMs = 600000) {
    const [weather, setWeather] = useState('--');

    useEffect(() => {
        let active = true;

        const poll = async () => {
            try {
                // Get real weather for Ho Chi Minh City (Lat 10.82, Lon 106.63)
                const res = await fetch(
                    'https://api.open-meteo.com/v1/forecast?latitude=10.82&longitude=106.63&current=temperature_2m,weather_code&timezone=Asia%2FBangkok'
                );
                const data = await res.json();
                
                if (active && data.current) {
                    const temp = Math.round(data.current.temperature_2m);
                    setWeather(`TP.HCM ${temp}°C`);
                }
            } catch {
                if (active) setWeather('--');
            }
        };

        poll();
        const id = setInterval(poll, intervalMs);
        return () => { active = false; clearInterval(id); };
    }, [intervalMs]);

    return weather;
}
