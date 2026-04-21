SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE elevator_ai;

DELETE FROM answers;
DELETE FROM prompts;
DELETE FROM intents;
DELETE FROM employees;

INSERT INTO intents (intent_name, domain, description) VALUES
('greeting', 'system', 'Lời chào mặc định của Sunybot'),
('elevator_speed', 'elevator', 'Tốc độ vận hành của thang máy'),
('elevator_overload', 'elevator', 'Hướng dẫn khi thang máy quá tải'),
('sos_usage', 'safety', 'Hướng dẫn sử dụng nút SOS');

INSERT INTO prompts (intent_id, prompt_text, embedding)
SELECT intent_id, 'Xin chào', NULL FROM intents WHERE intent_name = 'greeting'
UNION ALL
SELECT intent_id, 'Chào Sunybot', NULL FROM intents WHERE intent_name = 'greeting'
UNION ALL
SELECT intent_id, 'Tốc độ thang máy là bao nhiêu', NULL FROM intents WHERE intent_name = 'elevator_speed'
UNION ALL
SELECT intent_id, 'Thang máy chạy nhanh hay chậm', NULL FROM intents WHERE intent_name = 'elevator_speed'
UNION ALL
SELECT intent_id, 'Thang máy quá tải thì sao', NULL FROM intents WHERE intent_name = 'elevator_overload'
UNION ALL
SELECT intent_id, 'Nếu quá tải thì cần làm gì', NULL FROM intents WHERE intent_name = 'elevator_overload'
UNION ALL
SELECT intent_id, 'Nút SOS dùng để làm gì', NULL FROM intents WHERE intent_name = 'sos_usage'
UNION ALL
SELECT intent_id, 'Khi bị kẹt trong thang thì nhấn gì', NULL FROM intents WHERE intent_name = 'sos_usage';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id, 'Xin chào, tôi là Sunybot — trợ lý AI cho hệ thống thang máy thông minh.' FROM intents WHERE intent_name = 'greeting'
UNION ALL
SELECT intent_id, 'Tốc độ thang máy hiện tại trong dữ liệu mẫu là 1.2 m/s.' FROM intents WHERE intent_name = 'elevator_speed'
UNION ALL
SELECT intent_id, 'Khi thang máy quá tải, hệ thống sẽ cảnh báo, tạm không di chuyển và bạn nên giảm bớt số người hoặc tải trọng.' FROM intents WHERE intent_name = 'elevator_overload'
UNION ALL
SELECT intent_id, 'Nút SOS dùng để gửi tín hiệu khẩn cấp tới bộ phận hỗ trợ; khi gặp sự cố hãy giữ bình tĩnh, nhấn SOS và chờ hướng dẫn.' FROM intents WHERE intent_name = 'sos_usage';

INSERT INTO employees (
    employee_code,
    full_name,
    birth_year,
    position,
    department,
    hometown,
    phone,
    email,
    photo_path
) VALUES
('NV001', 'Nguyễn Văn A', 1995, 'Kỹ sư vận hành', 'Kỹ thuật', 'Hà Nội', '0901234567', 'a.nguyen@company.com', NULL),
('NV020', 'Nguyen Chan Huy', 1998, 'Kỹ sư AI', 'R&D', 'TP.HCM', '0988123123', 'huy.nguyen@company.com', NULL);
