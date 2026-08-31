import React from 'react';
import './BotOrb.css';

/**
 * @param {{ mode: 'idle'|'listening'|'speaking', title?: string, modeLabel?: string, stateText?: string }} props
 */
export default function BotOrb({ mode = 'idle', title = 'Sunybot', modeLabel, stateText }) {
    const modeText = modeLabel ||
        (mode === 'listening' ? 'Chế độ: Đang nghe' :
            mode === 'speaking' ? 'Chế độ: Đang trả lời' :
                'Chế độ: Bình thường');

    return (
        <div className={`bot-shell ${mode !== 'idle' ? mode : ''}`}>
            <div className="bot-head">
                <div className="sunyTitle">{title}</div>
                <div className="bot-mode">{modeText}</div>
            </div>
            <div className="orbFrame">
                <div className="orb"></div>
            </div>
            {stateText && <div className="state">{stateText}</div>}
        </div>
    );
}
