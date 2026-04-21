USE elevator_ai;

-- =========================================================
-- 0) EMPLOYEES: thêm nhân viên (không trùng employee_code)
-- =========================================================
INSERT INTO employees (employee_code, full_name, birth_year, position, department, hometown, phone, email, photo_path)
SELECT * FROM (
  SELECT 'NV001' AS employee_code, 'Nguyễn Văn A' AS full_name, 1995 AS birth_year, 'Kỹ sư vận hành' AS position, 'Kỹ thuật' AS department, 'Hà Nội' AS hometown, '0901234567' AS phone, 'a.nguyen@company.com' AS email, NULL AS photo_path
  UNION ALL SELECT 'NV020','Nguyễn Chấn Huy',2004,'Embedded Software Engineer','Kỹ thuật','TP. Hồ Chí Minh','0879459280','nguyenchanhuy151104@gmail.com',NULL
  UNION ALL SELECT 'NV015','Nguyễn Văn Đạt',2004,'LLM Engineer','Kỹ thuật','TP. Hồ Chí Minh','0901234567','user15022004@gmail.com',NULL
  UNION ALL SELECT 'NV140','Nguyễn Ngọc Tuấn',2004,'Computer Vision Engineer','Kỹ thuật','TP. Hồ Chí Minh','090123456','user21052004@gmail.com',NULL
  UNION ALL SELECT 'NV181','Lê Thị Nghi Lộc',2004,'Kỹ sư vận hành','Kỹ thuật','TP. Hồ Chí Minh','0909123456','nghiloc@company.com',NULL
  UNION ALL SELECT 'NV102','Trần Minh Khôi',1998,'Tổ trưởng bảo trì','Kỹ thuật','Đà Nẵng','0912345678','khoi.tran@company.com',NULL
  UNION ALL SELECT 'NV077','Phạm Thị Lan',1997,'Hành chính nhân sự','Hành chính','Hà Nội','0987654321','lan.pham@company.com',NULL
  UNION ALL SELECT 'NV055','Lê Quốc Bảo',1996,'Giám sát an ninh','An ninh','TP. Hồ Chí Minh','0933555777','bao.le@company.com',NULL
) AS v
WHERE NOT EXISTS (
  SELECT 1 FROM employees e WHERE e.employee_code = v.employee_code
);

-- =========================================================
-- 1) INTENTS: thêm intent (không trùng intent_name)
-- =========================================================
INSERT INTO intents (intent_name, domain, description)
SELECT * FROM (
  SELECT 'greeting' AS intent_name, 'general' AS domain, 'Câu chào hỏi cơ bản' AS description
  UNION ALL SELECT 'elevator_speed','elevator','Tốc độ thang máy'
  UNION ALL SELECT 'elevator_capacity','elevator','Tải trọng / số người tối đa'
  UNION ALL SELECT 'elevator_floor_time','elevator','Thời gian di chuyển giữa các tầng'
  UNION ALL SELECT 'elevator_door','elevator','Cửa thang máy: mở/đóng và an toàn cửa'
  UNION ALL SELECT 'elevator_emergency','safety','Xử lý tình huống khẩn cấp khi kẹt thang'
  UNION ALL SELECT 'elevator_power_outage','safety','Mất điện khi đang đi thang'
  UNION ALL SELECT 'elevator_fire','safety','Quy trình khi có cháy'
  UNION ALL SELECT 'elevator_overload','safety','Cảnh báo quá tải'
  UNION ALL SELECT 'elevator_maintenance','maintenance','Bảo trì định kỳ và lịch bảo trì'
  UNION ALL SELECT 'elevator_contact','support','Liên hệ hỗ trợ kỹ thuật'
  UNION ALL SELECT 'elevator_rules','policy','Quy định sử dụng thang máy'
  UNION ALL SELECT 'employee_lookup','hr','Tra cứu thông tin nhân viên theo mã/họ tên'
) AS v
WHERE NOT EXISTS (
  SELECT 1 FROM intents i WHERE i.intent_name = v.intent_name
);

-- =========================================================
-- 2) ANSWERS: mỗi intent 1 câu trả lời chuẩn (không trùng intent_id + answer_text)
-- =========================================================
-- greeting
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Xin chào! Tôi là Sunybot. Tôi có thể hỗ trợ gì cho bạn về thang máy hoặc tra cứu nhân viên?'
FROM intents i
WHERE i.intent_name='greeting'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Xin chào! Tôi là Sunybot. Tôi có thể hỗ trợ gì cho bạn về thang máy hoặc tra cứu nhân viên?'
);

-- elevator_speed
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Tốc độ thang máy hiện tại là 1.2 m/s.'
FROM intents i
WHERE i.intent_name='elevator_speed'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Tốc độ thang máy hiện tại là 1.2 m/s.'
);

-- elevator_capacity
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Tải trọng tối đa của thang máy là 1000 kg (khoảng 13 người).'
FROM intents i
WHERE i.intent_name='elevator_capacity'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Tải trọng tối đa của thang máy là 1000 kg (khoảng 13 người).'
);

-- elevator_floor_time
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Thời gian di chuyển giữa hai tầng liền kề trung bình khoảng 3–6 giây (tuỳ tải và khoảng cách).'
FROM intents i
WHERE i.intent_name='elevator_floor_time'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Thời gian di chuyển giữa hai tầng liền kề trung bình khoảng 3–6 giây (tuỳ tải và khoảng cách).'
);

-- elevator_door
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Cửa thang sẽ tự đóng sau vài giây; nếu có vật cản, cảm biến sẽ tự mở lại để đảm bảo an toàn.'
FROM intents i
WHERE i.intent_name='elevator_door'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Cửa thang sẽ tự đóng sau vài giây; nếu có vật cản, cảm biến sẽ tự mở lại để đảm bảo an toàn.'
);

-- elevator_emergency
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Nếu bị kẹt thang: giữ bình tĩnh, bấm nút chuông/Intercom, chờ kỹ thuật; không cạy cửa hoặc tự thoát ra.'
FROM intents i
WHERE i.intent_name='elevator_emergency'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Nếu bị kẹt thang: giữ bình tĩnh, bấm nút chuông/Intercom, chờ kỹ thuật; không cạy cửa hoặc tự thoát ra.'
);

-- elevator_power_outage
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Khi mất điện, thang thường kích hoạt nguồn dự phòng và đưa cabin về tầng gần nhất; hãy chờ hướng dẫn qua intercom.'
FROM intents i
WHERE i.intent_name='elevator_power_outage'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Khi mất điện, thang thường kích hoạt nguồn dự phòng và đưa cabin về tầng gần nhất; hãy chờ hướng dẫn qua intercom.'
);

-- elevator_fire
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Khi có cháy: không sử dụng thang máy, ưu tiên thang bộ theo lối thoát hiểm và làm theo hướng dẫn PCCC.'
FROM intents i
WHERE i.intent_name='elevator_fire'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Khi có cháy: không sử dụng thang máy, ưu tiên thang bộ theo lối thoát hiểm và làm theo hướng dẫn PCCC.'
);

-- elevator_overload
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Nếu thang báo quá tải, vui lòng giảm bớt người/hàng hoá cho đến khi cảnh báo tắt rồi mới vận hành.'
FROM intents i
WHERE i.intent_name='elevator_overload'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Nếu thang báo quá tải, vui lòng giảm bớt người/hàng hoá cho đến khi cảnh báo tắt rồi mới vận hành.'
);

-- elevator_maintenance
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Thang máy được bảo trì định kỳ hàng tháng; nếu cần hỗ trợ gấp, hãy liên hệ kỹ thuật theo mục “liên hệ”.'
FROM intents i
WHERE i.intent_name='elevator_maintenance'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Thang máy được bảo trì định kỳ hàng tháng; nếu cần hỗ trợ gấp, hãy liên hệ kỹ thuật theo mục “liên hệ”.'
);

-- elevator_contact
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Liên hệ hỗ trợ kỹ thuật: Phòng Kỹ thuật (máy lẻ 101) hoặc gọi 0901 234 567.'
FROM intents i
WHERE i.intent_name='elevator_contact'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Liên hệ hỗ trợ kỹ thuật: Phòng Kỹ thuật (máy lẻ 101) hoặc gọi 0901 234 567.'
);

-- elevator_rules
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Quy định: không chen lấn, không chèn cửa, không vận chuyển hàng dễ cháy nổ; ưu tiên người già/trẻ em.'
FROM intents i
WHERE i.intent_name='elevator_rules'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Quy định: không chen lấn, không chèn cửa, không vận chuyển hàng dễ cháy nổ; ưu tiên người già/trẻ em.'
);

-- employee_lookup
INSERT INTO answers (intent_id, answer_text)
SELECT i.intent_id, 'Bạn hãy nhập mã nhân viên (ví dụ NV020) hoặc họ tên để tôi tra cứu.'
FROM intents i
WHERE i.intent_name='employee_lookup'
AND NOT EXISTS (
  SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id
  AND a.answer_text='Bạn hãy nhập mã nhân viên (ví dụ NV020) hoặc họ tên để tôi tra cứu.'
);

-- =========================================================
-- 3) PROMPTS: thêm nhiều câu hỏi mẫu cho mỗi intent (không trùng intent_id + prompt_text)
-- =========================================================

-- greeting prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Xin chào' AS prompt_text
  UNION ALL SELECT 'Chào bạn'
  UNION ALL SELECT 'Hi'
  UNION ALL SELECT 'Hello'
  UNION ALL SELECT 'Bạn là ai?'
  UNION ALL SELECT 'Bạn tên gì?'
) v
WHERE i.intent_name='greeting'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_speed prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Tốc độ thang máy là bao nhiêu?' AS prompt_text
  UNION ALL SELECT 'Thang máy chạy nhanh hay chậm?'
  UNION ALL SELECT 'Tốc độ thang hiện tại?'
  UNION ALL SELECT 'Cho tôi biết tốc độ thang máy'
) v
WHERE i.intent_name='elevator_speed'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_capacity prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Thang máy chở được bao nhiêu người?' AS prompt_text
  UNION ALL SELECT 'Tải trọng tối đa của thang máy là bao nhiêu?'
  UNION ALL SELECT 'Thang chịu được bao nhiêu kg?'
  UNION ALL SELECT 'Quá tải là khi nào?'
) v
WHERE i.intent_name='elevator_capacity'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_floor_time prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Đi từ tầng 1 lên tầng 5 mất bao lâu?' AS prompt_text
  UNION ALL SELECT 'Thời gian di chuyển giữa các tầng là bao nhiêu?'
  UNION ALL SELECT 'Thang máy đi giữa 2 tầng mất mấy giây?'
) v
WHERE i.intent_name='elevator_floor_time'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_door prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Cửa thang máy tự đóng sau bao lâu?' AS prompt_text
  UNION ALL SELECT 'Cửa thang bị kẹt phải làm sao?'
  UNION ALL SELECT 'Có được chèn cửa thang máy không?'
  UNION ALL SELECT 'Cảm biến cửa thang hoạt động thế nào?'
) v
WHERE i.intent_name='elevator_door'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_emergency prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Tôi bị kẹt trong thang máy phải làm sao?' AS prompt_text
  UNION ALL SELECT 'Thang máy dừng đột ngột phải xử lý thế nào?'
  UNION ALL SELECT 'Bấm nút nào khi thang bị kẹt?'
) v
WHERE i.intent_name='elevator_emergency'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_power_outage prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Mất điện khi đang đi thang máy thì sao?' AS prompt_text
  UNION ALL SELECT 'Thang máy có nguồn dự phòng không?'
  UNION ALL SELECT 'Mất điện thang có tự về tầng không?'
) v
WHERE i.intent_name='elevator_power_outage'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_fire prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Khi có cháy có nên dùng thang máy không?' AS prompt_text
  UNION ALL SELECT 'Có cháy thì xử lý thế nào khi đang ở thang máy?'
  UNION ALL SELECT 'Quy trình PCCC liên quan thang máy?'
) v
WHERE i.intent_name='elevator_fire'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_overload prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Thang máy báo quá tải phải làm sao?' AS prompt_text
  UNION ALL SELECT 'Cảnh báo quá tải nghĩa là gì?'
  UNION ALL SELECT 'Vì sao thang kêu beep liên tục?'
) v
WHERE i.intent_name='elevator_overload'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_maintenance prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Bao lâu thì bảo trì thang máy một lần?' AS prompt_text
  UNION ALL SELECT 'Lịch bảo trì thang máy như thế nào?'
  UNION ALL SELECT 'Thang máy cần kiểm tra định kỳ không?'
) v
WHERE i.intent_name='elevator_maintenance'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_contact prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Liên hệ kỹ thuật thang máy ở đâu?' AS prompt_text
  UNION ALL SELECT 'Số điện thoại hỗ trợ thang máy là gì?'
  UNION ALL SELECT 'Có sự cố thang máy gọi ai?'
) v
WHERE i.intent_name='elevator_contact'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- elevator_rules prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Quy định sử dụng thang máy là gì?' AS prompt_text
  UNION ALL SELECT 'Có được chèn cửa thang máy không?'
  UNION ALL SELECT 'Có được vận chuyển hàng dễ cháy nổ bằng thang máy không?'
  UNION ALL SELECT 'Có ưu tiên người già và trẻ em không?'
) v
WHERE i.intent_name='elevator_rules'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- employee_lookup prompts
INSERT INTO prompts (intent_id, prompt_text)
SELECT i.intent_id, v.prompt_text
FROM intents i
JOIN (
  SELECT 'Tra cứu nhân viên NV020' AS prompt_text
  UNION ALL SELECT 'Thông tin nhân viên NV001' 
  UNION ALL SELECT 'Tìm thông tin nhân viên theo mã'
  UNION ALL SELECT 'Tìm nhân viên theo họ tên'
) v
WHERE i.intent_name='employee_lookup'
AND NOT EXISTS (
  SELECT 1 FROM prompts p WHERE p.intent_id=i.intent_id AND p.prompt_text=v.prompt_text
);

-- =========================================================
-- 4) DONE
-- =========================================================
SELECT 'SEED_FULL_DONE' AS status;

