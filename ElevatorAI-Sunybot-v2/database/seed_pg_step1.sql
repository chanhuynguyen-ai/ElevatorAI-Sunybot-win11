TRUNCATE TABLE chat_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE answers RESTART IDENTITY CASCADE;
TRUNCATE TABLE prompts RESTART IDENTITY CASCADE;
TRUNCATE TABLE intents RESTART IDENTITY CASCADE;
TRUNCATE TABLE employees RESTART IDENTITY CASCADE;

INSERT INTO intents (intent_name, domain, description, priority) VALUES
('greeting', 'system', 'Loi chao va gioi thieu Sunybot', 5),
('thanks', 'system', 'Phan hoi khi nguoi dung cam on', 8),
('elevator_status', 'elevator', 'Trang thai hien tai cua thang may', 10),
('elevator_speed', 'elevator', 'Thong tin ve toc do van hanh', 20),
('door_status', 'elevator', 'Trang thai cua thang may', 20),
('elevator_overload', 'elevator', 'Huong dan khi thang may qua tai', 15),
('capacity_limit', 'safety', 'So nguoi va tai trong toi da', 18),
('call_elevator', 'control', 'Huong dan goi thang may', 12),
('locked_floor', 'control', 'Giai thich tang bi khoa va cach xu ly', 18),
('sos_usage', 'safety', 'Huong dan su dung nut SOS', 12),
('power_failure', 'safety', 'Xu ly khi mat dien hoac dung khan cap', 12),
('maintenance_schedule', 'maintenance', 'Thong tin bao tri va kiem tra dinh ky', 25),
('safety_guideline', 'safety', 'Nguyen tac an toan khi su dung thang may', 20),
('emergency_support', 'safety', 'Tro giup khi bi ket trong thang may', 10);

INSERT INTO prompts (intent_id, prompt_text, prompt_norm, source_tag, meta)
SELECT intent_id, x.prompt_text, x.prompt_norm, 'seed_step1', x.meta
FROM intents i
JOIN (
    VALUES
    ('greeting', 'Xin chao', 'xin chao', '{"screen":"assistant","domain":"system","variant":"greeting"}'::jsonb),
    ('greeting', 'Chao Sunybot', 'chao sunybot', '{"screen":"assistant","domain":"system","variant":"greeting"}'::jsonb),
    ('greeting', 'Hello ban oi', 'hello ban oi', '{"screen":"assistant","domain":"system","variant":"greeting"}'::jsonb),
    ('greeting', 'Ban la ai', 'ban la ai', '{"screen":"assistant","domain":"system","variant":"intro"}'::jsonb),
    ('greeting', 'Gioi thieu ve Sunybot', 'gioi thieu ve sunybot', '{"screen":"assistant","domain":"system","variant":"intro"}'::jsonb),

    ('thanks', 'Cam on ban', 'cam on ban', '{"screen":"assistant","domain":"system"}'::jsonb),
    ('thanks', 'Cam on Sunybot', 'cam on sunybot', '{"screen":"assistant","domain":"system"}'::jsonb),
    ('thanks', 'Rat huu ich cam on', 'rat huu ich cam on', '{"screen":"assistant","domain":"system"}'::jsonb),

    ('elevator_status', 'Trang thai thang may hien tai', 'trang thai thang may hien tai', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_status', 'Thang may dang o tang may', 'thang may dang o tang may', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_status', 'Cabin dang o dau', 'cabin dang o dau', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_status', 'Thang may dang len hay xuong', 'thang may dang len hay xuong', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_status', 'Tinh hinh van hanh thang may', 'tinh hinh van hanh thang may', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_status', 'Trang thai cabin hien gio', 'trang thai cabin hien gio', '{"screen":"assistant","domain":"elevator"}'::jsonb),

    ('elevator_speed', 'Toc do thang may la bao nhieu', 'toc do thang may la bao nhieu', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_speed', 'Thang may chay nhanh hay cham', 'thang may chay nhanh hay cham', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_speed', 'Van toc van hanh cua thang may', 'van toc van hanh cua thang may', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_speed', 'Toc do mac dinh cua elevator', 'toc do mac dinh cua elevator', '{"screen":"assistant","domain":"elevator"}'::jsonb),

    ('door_status', 'Cua thang may dang mo hay dong', 'cua thang may dang mo hay dong', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('door_status', 'Trang thai cua cabin', 'trang thai cua cabin', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('door_status', 'Cua thang may co dang kep khong', 'cua thang may co dang kep khong', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('door_status', 'Bao loi cua thang may', 'bao loi cua thang may', '{"screen":"assistant","domain":"elevator"}'::jsonb),

    ('elevator_overload', 'Thang may qua tai thi sao', 'thang may qua tai thi sao', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_overload', 'Neu qua tai thi can lam gi', 'neu qua tai thi can lam gi', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_overload', 'Qua tai co di duoc khong', 'qua tai co di duoc khong', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_overload', 'Bao tai cua thang may nghia la gi', 'bao tai cua thang may nghia la gi', '{"screen":"assistant","domain":"elevator"}'::jsonb),
    ('elevator_overload', 'Lam sao khi chuong bao qua tai keu', 'lam sao khi chuong bao qua tai keu', '{"screen":"assistant","domain":"elevator"}'::jsonb),

    ('capacity_limit', 'Thang may toi da bao nhieu nguoi', 'thang may toi da bao nhieu nguoi', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('capacity_limit', 'Tai trong toi da cua thang may', 'tai trong toi da cua thang may', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('capacity_limit', 'So nguoi duoc phep vao cabin', 'so nguoi duoc phep vao cabin', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('capacity_limit', 'Gioi han trong luong thang may', 'gioi han trong luong thang may', '{"screen":"assistant","domain":"safety"}'::jsonb),

    ('call_elevator', 'Cach goi thang may', 'cach goi thang may', '{"screen":"assistant","domain":"control"}'::jsonb),
    ('call_elevator', 'Muon goi thang len tang nay thi lam sao', 'muon goi thang len tang nay thi lam sao', '{"screen":"assistant","domain":"control"}'::jsonb),
    ('call_elevator', 'Nhan nut nao de goi thang', 'nhan nut nao de goi thang', '{"screen":"assistant","domain":"control"}'::jsonb),
    ('call_elevator', 'Cach bam goi thang may', 'cach bam goi thang may', '{"screen":"assistant","domain":"control"}'::jsonb),

    ('locked_floor', 'Tai sao tang nay bi khoa', 'tai sao tang nay bi khoa', '{"screen":"assistant","domain":"control"}'::jsonb),
    ('locked_floor', 'Khong bam duoc tang can den', 'khong bam duoc tang can den', '{"screen":"assistant","domain":"control"}'::jsonb),
    ('locked_floor', 'Tang bi vo hieu hoa thi sao', 'tang bi vo hieu hoa thi sao', '{"screen":"assistant","domain":"control"}'::jsonb),
    ('locked_floor', 'Can quyen gi de di tang khoa', 'can quyen gi de di tang khoa', '{"screen":"assistant","domain":"control"}'::jsonb),

    ('sos_usage', 'Nut SOS dung de lam gi', 'nut sos dung de lam gi', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('sos_usage', 'Khi bi ket trong thang thi nhan gi', 'khi bi ket trong thang thi nhan gi', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('sos_usage', 'Khi nao can bam sos', 'khi nao can bam sos', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('sos_usage', 'Bam sos co ket noi duoc bao ve khong', 'bam sos co ket noi duoc bao ve khong', '{"screen":"assistant","domain":"safety"}'::jsonb),

    ('power_failure', 'Mat dien trong thang may thi sao', 'mat dien trong thang may thi sao', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('power_failure', 'Neu thang may dung dot ngot can lam gi', 'neu thang may dung dot ngot can lam gi', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('power_failure', 'Khi mat nguon cabin co den du phong khong', 'khi mat nguon cabin co den du phong khong', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('power_failure', 'Xu ly khi thang may mat dien', 'xu ly khi thang may mat dien', '{"screen":"assistant","domain":"safety"}'::jsonb),

    ('maintenance_schedule', 'Bao tri thang may dinh ky nhu the nao', 'bao tri thang may dinh ky nhu the nao', '{"screen":"assistant","domain":"maintenance"}'::jsonb),
    ('maintenance_schedule', 'Bao lau kiem tra thang may mot lan', 'bao lau kiem tra thang may mot lan', '{"screen":"assistant","domain":"maintenance"}'::jsonb),
    ('maintenance_schedule', 'Lich bao tri cua he thong', 'lich bao tri cua he thong', '{"screen":"assistant","domain":"maintenance"}'::jsonb),
    ('maintenance_schedule', 'Can bao tri nhung gi', 'can bao tri nhung gi', '{"screen":"assistant","domain":"maintenance"}'::jsonb),

    ('safety_guideline', 'Nhung luu y an toan khi di thang may', 'nhung luu y an toan khi di thang may', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('safety_guideline', 'Dung thang may sao cho an toan', 'dung thang may sao cho an toan', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('safety_guideline', 'Tre em di thang may can chu y gi', 'tre em di thang may can chu y gi', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('safety_guideline', 'Nguoi gia dung thang may can luu y gi', 'nguoi gia dung thang may can luu y gi', '{"screen":"assistant","domain":"safety"}'::jsonb),

    ('emergency_support', 'Toi dang bi ket trong thang may', 'toi dang bi ket trong thang may', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('emergency_support', 'Hay giup toi toi bi mac ket', 'hay giup toi toi bi mac ket', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('emergency_support', 'Can ho tro khan cap trong cabin', 'can ho tro khan cap trong cabin', '{"screen":"assistant","domain":"safety"}'::jsonb),
    ('emergency_support', 'Toi hoang so khi thang dung dot ngot', 'toi hoang so khi thang dung dot ngot', '{"screen":"assistant","domain":"safety"}'::jsonb)
) AS x(intent_name, prompt_text, prompt_norm, meta)
ON x.intent_name = i.intent_name;

INSERT INTO answers (intent_id, answer_text, answer_type, source_note)
SELECT intent_id, answer_text, answer_type, source_note
FROM (
    VALUES
    ('greeting', 'Xin chao, toi la Sunybot - tro ly AI ho tro he thong thang may thong minh. Toi co the giai dap thong tin van hanh, an toan, bao tri va tra cuu nhan vien.', 'default', 'seed_step1'),
    ('thanks', 'Rat vui duoc ho tro ban. Neu can them thong tin ve thang may, an toan hoac nhan vien, cu hoi toi.', 'default', 'seed_step1'),
    ('elevator_status', 'Trong che do du lieu mau, thang may dang o tang 5, cua dong, di chuyen binh thuong va huong len. Khi ket noi du lieu realtime, cau tra loi nay se duoc cap nhat theo API.', 'default', 'seed_step1'),
    ('elevator_speed', 'Trong cau hinh mau hien tai, toc do van hanh danh nghia cua thang may la 1.2 m/s. Toc do thuc te co the duoc giam o che do bao tri hoac tiet kiem nang luong.', 'default', 'seed_step1'),
    ('door_status', 'Trang thai cua can duoc theo doi theo cac nhan OPEN, CLOSED hoac JAM. Neu cua kep, khong co va vat can thi khong nen co mo bang tay, hay bao ky thuat vien kiem tra.', 'default', 'seed_step1'),
    ('elevator_overload', 'Khi qua tai, he thong se phat canh bao, tam ngung di chuyen va khong dong lenh di tang. Ban nen giam bot so nguoi hoac tai trong roi thu lai.', 'default', 'seed_step1'),
    ('capacity_limit', 'Tai trong toi da can duoc tuan theo dung theo tem tai trong trong cabin. Trong du lieu mau, can uu tien khong vuot qua muc danh dinh va khong chen lan khi da dong nguong tai trong.', 'default', 'seed_step1'),
    ('call_elevator', 'De goi thang may, ban nhan nut len hoac xuong o ben ngoai cabin, sau do doi den khi thang den dung tang. Khi vao cabin, nhan tang can den mot lan ro rang.', 'default', 'seed_step1'),
    ('locked_floor', 'Tang bi khoa thuong can quyen truy cap, the tu, mat khau hoac duoc mo trong gio nhat dinh. Neu khong bam duoc tang, hay kiem tra quyen truy cap hoac lien he bo phan quan tri toa nha.', 'default', 'seed_step1'),
    ('sos_usage', 'Nut SOS dung de gui yeu cau khan cap toi bo phan ho tro. Khi gap su co, hay giu binh tinh, bam SOS, dung tuong vao cua va cho huong dan.', 'default', 'seed_step1'),
    ('power_failure', 'Khi mat dien hoac thang dung dot ngot, hay giu binh tinh, khong co mo cua bang tay, su dung den cabin neu co, bam SOS hoac lien lac intercom va cho cuu ho.', 'default', 'seed_step1'),
    ('maintenance_schedule', 'Bao tri dinh ky nen bao gom kiem tra cua, bo dieu khien, phanh, tin hieu tang, den cabin, quat thong gio va he thong cuu ho. Tan suat thuong la hang thang va kiem dinh theo quy dinh.', 'default', 'seed_step1'),
    ('safety_guideline', 'Khi su dung thang may, hay xep hang gon, khong chen khi cua dang dong, giu tre em dung gan nguoi lon, va khong dung thang may khi co chay no neu toa nha co quy dinh cau thang bo.', 'default', 'seed_step1'),
    ('emergency_support', 'Neu ban dang bi ket trong thang may, hay giu binh tinh, dung ngoi sat cua, bam SOS hoac nut lien lac, thong bao so nguoi trong cabin va cho doi huong dan tu bo phan ho tro.', 'default', 'seed_step1')
) AS a(intent_name, answer_text, answer_type, source_note)
JOIN intents i ON i.intent_name = a.intent_name;

INSERT INTO employees (
    employee_code,
    full_name,
    full_name_norm,
    birth_year,
    position,
    department,
    hometown,
    phone,
    email,
    photo_path,
    status
) VALUES
('NV001', 'Nguyen Van An', 'nguyen van an', 1994, 'Ky su van hanh', 'Ky thuat', 'Ha Noi', '0901234567', 'an.nguyen@company.com', NULL, 'active'),
('NV005', 'Tran Minh Chau', 'tran minh chau', 1996, 'Nhan vien bao tri', 'Bao tri', 'Da Nang', '0905556677', 'chau.tran@company.com', NULL, 'active'),
('NV012', 'Le Quoc Bao', 'le quoc bao', 1993, 'Ky su dien dieu khien', 'R&D', 'Can Tho', '0911223344', 'bao.le@company.com', NULL, 'active'),
('NV020', 'Nguyen Chan Huy', 'nguyen chan huy', 1998, 'Ky su AI', 'R&D', 'TP HCM', '0988123123', 'huy.nguyen@company.com', NULL, 'active'),
('NV028', 'Pham Thu Ha', 'pham thu ha', 1997, 'Nhan vien truc tong dai', 'Ho tro khach hang', 'Hai Phong', '0933445566', 'ha.pham@company.com', NULL, 'active'),
('NV031', 'Vo Duc Long', 'vo duc long', 1991, 'Quan ly van hanh', 'Van hanh', 'Lam Dong', '0977889900', 'long.vo@company.com', NULL, 'active');
