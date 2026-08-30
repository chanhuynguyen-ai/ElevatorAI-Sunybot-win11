/* ===== SPEECH SERVICE ===== */

export function speak(text) {
    if (!window.speechSynthesis) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'vi-VN';
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
}

export function cancelSpeech() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
}

export function getSpeechRecognition() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

/**
 * Start wake-word listening. Returns a cleanup function.
 * onWakeCommand(text) is called when "hey sunybot" is followed by a command.
 * onWakeOnly() is called when only wake word is detected.
 * onModeChange(mode) is called with 'listening' | 'speaking' | 'idle'.
 * onStateText(text) is called with status message.
 */
export function startWakeWordListener({ onWakeCommand, onWakeOnly, onModeChange, onStateText }) {
    const SR = getSpeechRecognition();
    if (!SR) {
        onStateText?.('Không hỗ trợ STT trên trình duyệt này.');
        return () => { };
    }

    const rec = new SR();
    rec.lang = 'vi-VN';
    rec.continuous = true;
    rec.interimResults = true;

    let stopped = false;

    rec.onstart = () => {
        onModeChange?.('listening');
        onStateText?.('Đang nghe wake word…');
    };

    rec.onerror = () => {
        onModeChange?.('idle');
        onStateText?.('Mic lỗi — tự khôi phục...');
        if (!stopped) setTimeout(() => { try { rec.start(); } catch { } }, 800);
    };

    rec.onend = () => {
        onModeChange?.('idle');
        if (!stopped) setTimeout(() => { try { rec.start(); } catch { } }, 350);
    };

    let lastFinal = '';
    rec.onresult = async (ev) => {
        let transcript = '';
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
            transcript += ev.results[i][0].transcript;
        }
        transcript = transcript.trim().toLowerCase();

        const last = ev.results[ev.results.length - 1];
        if (!last || !last.isFinal) return;
        if (transcript === lastFinal) return;
        lastFinal = transcript;

        if (transcript.includes('hey sunybot') || transcript.includes('hey sunnybot')) {
            const after = transcript
                .replace('hey sunybot', '')
                .replace('hey sunnybot', '')
                .trim();

            if (!after) {
                onWakeOnly?.();
                return;
            }
            onWakeCommand?.(after);
        }
    };

    try { rec.start(); } catch { }

    return () => {
        stopped = true;
        try { rec.stop(); } catch { }
    };
}

/**
 * One-shot voice recognition. Calls onResult(text) when done.
 * stopWake/resumeWake are optional functions to pause wake-word during capture.
 */
export function voiceChatOnce(onResult, stopWake, resumeWake) {
    const SR = getSpeechRecognition();
    if (!SR) return;

    stopWake?.();

    const rec = new SR();
    rec.lang = 'vi-VN';
    rec.continuous = false;
    rec.interimResults = false;

    rec.onresult = (ev) => {
        const transcript = ev.results[0][0].transcript.trim();
        onResult?.(transcript);
    };

    rec.onerror = () => resumeWake?.();
    rec.onend = () => resumeWake?.();

    try { rec.start(); } catch { }
}
