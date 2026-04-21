-- Seed data for Windows-friendly Sunybot schema
-- Chay sau schema_pg_step1_windows.sql

INSERT INTO intents (intent_name, domain, description, priority, is_active)
VALUES
    ('customer_greeting', 'customer', 'Chao hoi co ban cho khach hang', 10, TRUE),
    ('customer_status', 'customer', 'Hoi trang thai thang may', 20, TRUE),
    ('customer_safety', 'customer', 'FAQ an toan thang may', 20, TRUE),
    ('maintenance_cv_summary', 'maintenance_cv', 'Tong hop du lieu CV cho ky thuat vien', 10, TRUE),
    ('maintenance_priority_alert', 'maintenance_cv', 'Canh bao uu tien can xu ly', 10, TRUE),
    ('maintenance_fall_count', 'maintenance_cv', 'Dem so lan te nga trong ngay', 10, TRUE),
    ('maintenance_person_seen', 'maintenance_cv', 'Nguoi duoc nhan dien gan nhat', 15, TRUE)
ON CONFLICT (intent_name) DO UPDATE SET
    domain = EXCLUDED.domain,
    description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active;

INSERT INTO prompts (intent_id, prompt_text, prompt_norm, lang, source_tag, is_active, meta)
SELECT i.intent_id, p.prompt_text, p.prompt_norm, 'vi', 'seed_windows', TRUE, p.meta::jsonb
FROM intents i
JOIN (
    VALUES
        ('customer_greeting', 'xin chao', 'xin chao', '{"scope":"customer","domain":"customer"}'),
        ('customer_greeting', 'chao sunybot', 'chao sunybot', '{"scope":"customer","domain":"customer"}'),
        ('customer_status', 'trang thai thang may hien tai', 'trang thai thang may hien tai', '{"scope":"customer","domain":"elevator_status"}'),
        ('customer_status', 'thang may dang o tang may', 'thang may dang o tang may', '{"scope":"customer","domain":"elevator_status"}'),
        ('customer_safety', 'neu bi ket trong thang may thi lam gi', 'neu bi ket trong thang may thi lam gi', '{"scope":"customer","domain":"guide"}'),
        ('customer_safety', 'qua tai thi nen lam gi', 'qua tai thi nen lam gi', '{"scope":"customer","domain":"guide"}'),
        ('maintenance_cv_summary', 'tom tat loi noi bat hom nay', 'tom tat loi noi bat hom nay', '{"scope":"maintenance","domain":"maintenance_cv"}'),
        ('maintenance_cv_summary', 'su kien cv noi bat hom nay', 'su kien cv noi bat hom nay', '{"scope":"maintenance","domain":"maintenance_cv"}'),
        ('maintenance_priority_alert', 'canh bao nao can uu tien xu ly', 'canh bao nao can uu tien xu ly', '{"scope":"maintenance","domain":"maintenance_cv"}'),
        ('maintenance_priority_alert', 'co canh bao nao can xu ly truoc khong', 'co canh bao nao can xu ly truoc khong', '{"scope":"maintenance","domain":"maintenance_cv"}'),
        ('maintenance_fall_count', 'hom nay co bao nhieu lan te nga', 'hom nay co bao nhieu lan te nga', '{"scope":"maintenance","domain":"maintenance_cv"}'),
        ('maintenance_person_seen', 'nguoi duoc nhan dien gan nhat la ai', 'nguoi duoc nhan dien gan nhat la ai', '{"scope":"maintenance","domain":"maintenance_cv"}')
) AS p(intent_name, prompt_text, prompt_norm, meta)
ON i.intent_name = p.intent_name
ON CONFLICT (intent_id, prompt_text) DO UPDATE SET
    prompt_norm = EXCLUDED.prompt_norm,
    source_tag = EXCLUDED.source_tag,
    is_active = EXCLUDED.is_active,
    meta = EXCLUDED.meta;

INSERT INTO answers (intent_id, answer_text, answer_type, source_note, is_active)
SELECT i.intent_id, a.answer_text, 'default', 'seed_windows', TRUE
FROM intents i
JOIN (
    VALUES
        ('customer_greeting', 'Xin chào, tôi là Sunybot. Tôi có thể hỗ trợ trạng thái thang máy, hướng dẫn sử dụng và thông tin an toàn.'),
        ('customer_status', 'Tôi sẽ kiểm tra trạng thái thang máy hiện tại và trả lời dựa trên dữ liệu hệ thống mới nhất.'),
        ('customer_safety', 'Nếu xảy ra sự cố, hãy giữ bình tĩnh, bấm SOS hoặc liên hệ bộ phận kỹ thuật. Không cố cạy cửa khi thang chưa dừng an toàn.'),
        ('maintenance_cv_summary', 'Tôi sẽ tổng hợp sự kiện camera, tình trạng đông người, té ngã và bất thường mới nhất từ elevator_cv.'),
        ('maintenance_priority_alert', 'Tôi sẽ ưu tiên các cảnh báo FALL, LYING, OVERLOAD và CROWD để hỗ trợ kỹ thuật viên xử lý nhanh hơn.'),
        ('maintenance_fall_count', 'Tôi sẽ kiểm tra số sự kiện FALL trong ngày hôm nay từ camera_events.'),
        ('maintenance_person_seen', 'Tôi sẽ kiểm tra người được nhận diện gần nhất từ dữ liệu camera_events.')
) AS a(intent_name, answer_text)
ON i.intent_name = a.intent_name
ON CONFLICT DO NOTHING;

INSERT INTO employees (
    employee_code, full_name, full_name_norm, department, position, role, status, password_hash, auth_source
)
VALUES (
    'KT001',
    'Nguyen Van Ky Thuat',
    'nguyen van ky thuat',
    'Bao tri',
    'Ky thuat vien',
    'maintenance',
    'active',
    '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92',
    'seed_windows'
)
ON CONFLICT (employee_code) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    full_name_norm = EXCLUDED.full_name_norm,
    department = EXCLUDED.department,
    position = EXCLUDED.position,
    role = EXCLUDED.role,
    status = EXCLUDED.status,
    password_hash = EXCLUDED.password_hash,
    auth_source = EXCLUDED.auth_source;
