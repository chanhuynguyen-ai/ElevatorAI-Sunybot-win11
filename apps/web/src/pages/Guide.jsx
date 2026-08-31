import React from 'react';
import './Guide.css';

const guides = [
    {
        icon: '🛗',
        title: 'Kẹt thang',
        content: 'Giữ bình tĩnh, bấm nút SOS hoặc chuông báo động. Đứng cách cửa an toàn và chờ đội kỹ thuật đến hỗ trợ. Không cố cạy cửa.',
    },
    {
        icon: '🔥',
        title: 'Cháy',
        content: 'Không sử dụng thang máy khi có cháy. Di chuyển bằng cầu thang bộ gần nhất. Dùng khăn ướt che mũi và báo nhân viên an toàn.',
    },
    {
        icon: '⚡',
        title: 'Mất điện',
        content: 'Thang sẽ tự động đưa về tầng gần nhất khi mất điện. Giữ bình tĩnh, không cạy cửa khi chưa có kỹ thuật viên hỗ trợ.',
    },
    {
        icon: '🌊',
        title: 'Ngập nước',
        content: 'Nếu phát hiện nước tràn vào thang máy, bấm nút dừng khẩn cấp. Di chuyển ra ngoài ngay khi cửa mở. Thông báo bảo trì.',
    },
    {
        icon: '🌍',
        title: 'Động đất',
        content: 'Nếu đang trong thang máy khi có động đất, bấm tất cả các nút tầng để dừng ở tầng gần nhất. Rời thang ngay khi cửa mở.',
    },
    {
        icon: '🤕',
        title: 'Tai nạn / Sức khỏe',
        content: 'Nếu có người bị thương hoặc ngất xỉu trong thang, bấm SOS ngay. Đưa thang về tầng gần nhất và gọi cấp cứu 115.',
    },
    {
        icon: '🌫️',
        title: 'Khói / Ngạt khí',
        content: 'Nếu xuất hiện khói hoặc khó thở trong cabin, cúi thấp người, che mũi bằng khăn và bấm SOS. Ra khỏi thang ngay khi cửa mở.',
    },
    {
        icon: '🚪',
        title: 'Cửa không mở',
        content: 'Không cố dùng tay cạy cửa. Bấm nút mở cửa, gọi SOS hoặc liên hệ bảo trì. Giữ khoảng cách với mép cửa khi thang dừng.',
    },
    {
        icon: '⚠️',
        title: 'Quá tải cabin',
        content: 'Nếu có cảnh báo quá tải, giảm bớt người hoặc hàng hóa trước khi tiếp tục di chuyển. Không cố vận hành thang khi chuông quá tải đang kêu.',
    },
];

export default function Guide() {
    return (
        <div>
            <div className="page-title">
                <h1>Hướng dẫn khẩn cấp</h1>
                <div className="meta">9 tình huống · Hướng dẫn xử lý</div>
            </div>

            <div className="guide-grid">
                {guides.map((g) => (
                    <div key={g.title} className="guide-card">
                        <div className="guide-icon">{g.icon}</div>
                        <h3>{g.title}</h3>
                        <div className="muted">{g.content}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
