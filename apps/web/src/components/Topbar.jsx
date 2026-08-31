import React from 'react';
import './Topbar.css';

export default function Topbar({ time, peopleCount, weather }) {
    return (
        <div className="suny-topbar">
            <div className="brand" aria-label="Sunybot">
                <span className="dot" aria-hidden="true"></span>
                <span>Sunybot • Smart Elevator</span>
            </div>
            <div className="right">
                <div className="suny-pill" title="Thời gian">
                    <span className="k">Giờ</span>
                    <span className="v">{time}</span>
                </div>
                <div className="suny-pill" title="Số lượng người trong thang">
                    <span className="k">Người</span>
                    <span className="v">{peopleCount}</span>
                </div>
                <div className="suny-pill" title="Thời tiết">
                    <span className="k">Thời tiết</span>
                    <span className="v">{weather}</span>
                </div>
            </div>
        </div>
    );
}
