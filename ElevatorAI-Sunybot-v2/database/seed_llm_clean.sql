BEGIN;

-- =========================
-- 1) INTENTS
-- =========================
INSERT INTO intents (intent_name, description) VALUES
('system_overview', 'FAQ tổng quan về hệ thống thang máy AI'),
('maintenance_workflow', 'Nghiệp vụ bảo trì và quy trình xử lý'),
('cv_alert_explain', 'Giải thích các cảnh báo từ module CV');

-- =========================
-- 2) ANSWERS
-- =========================

-- system_overview
INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Hệ thống thang máy AI là một nền tảng tích hợp giữa giao diện điều khiển thang máy, camera giám sát, cơ sở dữ liệu PostgreSQL và chatbot hỗ trợ. Mục tiêu của hệ thống là theo dõi trạng thái thang máy, ghi nhận sự kiện bất thường, hỗ trợ bảo trì và nâng cao trải nghiệm người dùng.$$ 
FROM intents WHERE intent_name = 'system_overview';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Kiến trúc hệ thống được tách làm hai phần dữ liệu chính: elevator_cv cho dữ liệu camera và elevator_llm cho dữ liệu tri thức chatbot. Phần CV chịu trách nhiệm nhận diện, ghi sự kiện và mật độ người; phần chatbot chịu trách nhiệm retrieval, semantic matching và diễn đạt câu trả lời tự nhiên.$$ 
FROM intents WHERE intent_name = 'system_overview';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Hệ thống này được thiết kế để chatbot không tự suy đoán dữ liệu camera. Những câu hỏi về số người, sự kiện, mật độ hoặc trạng thái phải lấy từ elevator_cv; còn những câu hỏi về hướng dẫn sử dụng, giải thích cảnh báo và quy trình nghiệp vụ sẽ lấy từ elevator_llm.$$ 
FROM intents WHERE intent_name = 'system_overview';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Màn hình chính phục vụ người dùng cuối, còn màn hình bảo trì phục vụ kỹ thuật viên. Màn bảo trì hiển thị camera realtime, timeline sự kiện, dữ liệu hệ thống và công cụ hỗ trợ truy vết để kiểm tra vận hành.$$ 
FROM intents WHERE intent_name = 'system_overview';

-- maintenance_workflow
INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Quy trình bảo trì nên bắt đầu bằng việc kiểm tra trạng thái tổng quát của thang máy, theo dõi camera realtime, xem timeline sự kiện gần đây và xác định xem có cảnh báo nghiêm trọng như fall, lying hoặc crowd hay không. Sau đó mới đi sâu vào phân tích dữ liệu và nguyên nhân.$$ 
FROM intents WHERE intent_name = 'maintenance_workflow';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Khi hệ thống phát hiện té ngã, kỹ thuật viên cần ưu tiên xác minh hình ảnh camera, kiểm tra thời điểm và vị trí sự kiện, sau đó liên hệ bộ phận phụ trách để xử lý khẩn cấp. Đây là loại cảnh báo có mức ưu tiên rất cao.$$ 
FROM intents WHERE intent_name = 'maintenance_workflow';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Khi có cảnh báo đông người, kỹ thuật viên nên kiểm tra số người hiện tại, thời điểm cao điểm và tần suất lặp lại, từ đó đánh giá có cần điều chỉnh vận hành hoặc cảnh báo người dùng hay không.$$ 
FROM intents WHERE intent_name = 'maintenance_workflow';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Đối với người chưa gán nhãn, quy trình đúng là xác minh lại từ camera, sau đó nếu cần thì dùng chức năng đăng ký khuôn mặt để tạo hồ sơ nhân viên trong person_registry và bổ sung dữ liệu nhận diện sau.$$ 
FROM intents WHERE intent_name = 'maintenance_workflow';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Khi chatbot bảo trì không tìm thấy tri thức phù hợp, kỹ thuật viên nên hỏi lại theo hướng rõ hơn như trạng thái hiện tại, sự kiện camera, hướng dẫn bảo trì hoặc giải thích cảnh báo. Điều này giúp hệ thống retrieval trả lời nhanh và chính xác hơn.$$ 
FROM intents WHERE intent_name = 'maintenance_workflow';

-- cv_alert_explain
INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Cảnh báo crowd cho biết số lượng người trong cabin hoặc vùng theo dõi vượt qua ngưỡng đã định. Đây không nhất thiết là lỗi phần cứng, nhưng là tín hiệu cần theo dõi vì có thể dẫn đến quá tải hoặc nguy cơ mất an toàn.$$ 
FROM intents WHERE intent_name = 'cv_alert_explain';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Cảnh báo fall cho biết hệ thống thị giác phát hiện khả năng có người bị ngã hoặc chuyển trạng thái bất thường. Đây là cảnh báo ưu tiên rất cao và cần được kiểm tra ngay.$$ 
FROM intents WHERE intent_name = 'cv_alert_explain';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Cảnh báo lying cho biết hệ thống phát hiện tư thế nằm hoặc nằm lâu bất thường. Trong môi trường thang máy, đây là tín hiệu quan trọng vì có thể liên quan đến tai nạn hoặc sự cố sức khỏe.$$ 
FROM intents WHERE intent_name = 'cv_alert_explain';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Cảnh báo bottle hoặc vật thể lạ cho biết camera phát hiện một vật cần chú ý trong cabin. Tùy chính sách vận hành, đây có thể là vật bỏ quên, vật cản hoặc tín hiệu cho hành vi bất thường.$$ 
FROM intents WHERE intent_name = 'cv_alert_explain';

INSERT INTO answers (intent_id, answer_text)
SELECT intent_id,
$$Cảnh báo unknown person cho biết hệ thống ghi nhận một người chưa được gán danh tính trong dữ liệu hiện có. Đây là tín hiệu để kỹ thuật viên xem xét việc gán nhãn hoặc đăng ký khuôn mặt.$$ 
FROM intents WHERE intent_name = 'cv_alert_explain';

-- =========================
-- 3) PROMPTS
-- =========================

-- system_overview
INSERT INTO prompts (intent_id, prompt_text, prompt_norm, meta)
SELECT i.intent_id, x.prompt_text, x.prompt_norm, x.meta::jsonb
FROM intents i
CROSS JOIN (
    VALUES
    ('Hệ thống này dùng để làm gì?', 'he thong nay dung de lam gi', '{"group":"faq_he_thong","domain":"system","scope":"general"}'),
    ('Mục tiêu của hệ thống thang máy AI là gì?', 'muc tieu cua he thong thang may ai la gi', '{"group":"faq_he_thong","domain":"system","scope":"general"}'),
    ('Sunybot có vai trò gì trong đề tài này?', 'sunybot co vai tro gi trong de tai nay', '{"group":"faq_he_thong","domain":"system","scope":"general"}'),
    ('Hệ thống gồm những thành phần nào?', 'he thong gom nhung thanh phan nao', '{"group":"faq_he_thong","domain":"system","scope":"general"}'),
    ('Kiến trúc tổng thể của hệ thống là gì?', 'kien truc tong the cua he thong la gi', '{"group":"faq_he_thong","domain":"system","scope":"maintenance"}'),
    ('Vì sao phải tách elevator_cv và elevator_llm?', 'vi sao phai tach elevator cv va elevator llm', '{"group":"faq_he_thong","domain":"system","scope":"maintenance"}'),
    ('Database elevator_cv dùng để làm gì?', 'database elevator cv dung de lam gi', '{"group":"faq_he_thong","domain":"system","scope":"maintenance"}'),
    ('Database elevator_llm dùng để làm gì?', 'database elevator llm dung de lam gi', '{"group":"faq_he_thong","domain":"system","scope":"maintenance"}'),
    ('Màn hình chính và màn hình bảo trì khác nhau như thế nào?', 'man hinh chinh va man hinh bao tri khac nhau nhu the nao', '{"group":"faq_he_thong","domain":"system","scope":"general"}'),
    ('Tại sao chatbot không được tự đoán dữ liệu camera?', 'tai sao chatbot khong duoc tu doan du lieu camera', '{"group":"faq_he_thong","domain":"system","scope":"maintenance"}'),
    ('Hệ thống này hỗ trợ người dùng và kỹ thuật viên như thế nào?', 'he thong nay ho tro nguoi dung va ky thuat vien nhu the nao', '{"group":"faq_he_thong","domain":"system","scope":"general"}'),
    ('Mối liên kết giữa CV service và chatbot là gì?', 'moi lien ket giua cv service va chatbot la gi', '{"group":"faq_he_thong","domain":"system","scope":"maintenance"}')
) AS x(prompt_text, prompt_norm, meta)
WHERE i.intent_name = 'system_overview';

-- maintenance_workflow
INSERT INTO prompts (intent_id, prompt_text, prompt_norm, meta)
SELECT i.intent_id, x.prompt_text, x.prompt_norm, x.meta::jsonb
FROM intents i
CROSS JOIN (
    VALUES
    ('Quy trình bảo trì cơ bản của hệ thống là gì?', 'quy trinh bao tri co ban cua he thong la gi', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Kỹ thuật viên nên kiểm tra gì đầu tiên?', 'ky thuat vien nen kiem tra gi dau tien', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Khi có cảnh báo fall thì phải xử lý thế nào?', 'khi co canh bao fall thi phai xu ly the nao', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Khi có cảnh báo crowd thì nên làm gì?', 'khi co canh bao crowd thi nen lam gi', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Khi có người chưa gán nhãn thì xử lý ra sao?', 'khi co nguoi chua gan nhan thi xu ly ra sao', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Đăng ký khuôn mặt nhân viên dùng trong trường hợp nào?', 'dang ky khuon mat nhan vien dung trong truong hop nao', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Khi chatbot không biết câu trả lời thì nên làm gì?', 'khi chatbot khong biet cau tra loi thi nen lam gi', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Làm sao để theo dõi sự kiện camera trên giao diện bảo trì?', 'lam sao de theo doi su kien camera tren giao dien bao tri', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Cần kiểm tra những mục nào trong trung tâm bảo trì?', 'can kiem tra nhung muc nao trong trung tam bao tri', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Quy trình xem log và dữ liệu camera là gì?', 'quy trinh xem log va du lieu camera la gi', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Khi có lỗi camera hoặc mất kết nối thì xử lý thế nào?', 'khi co loi camera hoac mat ket noi thi xu ly the nao', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}'),
    ('Làm sao để dùng chatbot bảo trì hiệu quả hơn?', 'lam sao de dung chatbot bao tri hieu qua hon', '{"group":"nghiep_vu_bao_tri","domain":"maintenance","scope":"maintenance"}')
) AS x(prompt_text, prompt_norm, meta)
WHERE i.intent_name = 'maintenance_workflow';

-- cv_alert_explain
INSERT INTO prompts (intent_id, prompt_text, prompt_norm, meta)
SELECT i.intent_id, x.prompt_text, x.prompt_norm, x.meta::jsonb
FROM intents i
CROSS JOIN (
    VALUES
    ('Cảnh báo crowd nghĩa là gì?', 'canh bao crowd nghia la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Crowd trong hệ thống camera là gì?', 'crowd trong he thong camera la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Cảnh báo fall nghĩa là gì?', 'canh bao fall nghia la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Fall trong hệ thống camera là gì?', 'fall trong he thong camera la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Cảnh báo lying là gì?', 'canh bao lying la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Lying trong hệ thống là gì?', 'lying trong he thong la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Cảnh báo bottle có ý nghĩa gì?', 'canh bao bottle co y nghia gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Bottle trong cabin nghĩa là gì?', 'bottle trong cabin nghia la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}'),
    ('Unknown person nghĩa là gì?', 'unknown person nghia la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"maintenance"}'),
    ('Người chưa gán nhãn là gì?', 'nguoi chua gan nhan la gi', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"maintenance"}'),
    ('Tại sao hệ thống báo phát hiện người chưa gán nhãn?', 'tai sao he thong bao phat hien nguoi chua gan nhan', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"maintenance"}'),
    ('Khi thấy cảnh báo CV thì nên hiểu thế nào?', 'khi thay canh bao cv thi nen hieu the nao', '{"group":"giai_thich_canh_bao_cv","domain":"cv_alert","scope":"general"}')
) AS x(prompt_text, prompt_norm, meta)
WHERE i.intent_name = 'cv_alert_explain';

INSERT INTO employees (employee_code, full_name, department, position)
VALUES ('NV001', 'Nguyen Van A', 'Ky thuat', 'Nhan vien mau')
ON CONFLICT (employee_code) DO NOTHING;

COMMIT;

