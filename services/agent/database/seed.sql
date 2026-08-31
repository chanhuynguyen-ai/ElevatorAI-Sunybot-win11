INSERT INTO intents (intent_name, domain, description, priority, is_active) VALUES
('customer_greeting','customer','Basic greeting',10,TRUE),
('customer_safety','customer','Elevator safety guidance',20,TRUE),
('maintenance_cv_summary','maintenance_cv','Summarize CV events for technicians',10,TRUE)
ON CONFLICT (intent_name) DO NOTHING;

INSERT INTO prompts (intent_id,prompt_text,prompt_norm,lang,source_tag,is_active,meta)
SELECT i.intent_id, x.prompt_text, x.prompt_norm, 'vi', 'demo_seed', TRUE, x.meta::jsonb
FROM intents i JOIN (VALUES
('customer_greeting','xin chao','xin chao','{"scope":"customer"}'),
('customer_safety','neu bi ket trong thang may thi lam gi','neu bi ket trong thang may thi lam gi','{"scope":"customer"}'),
('maintenance_cv_summary','tom tat su kien camera hom nay','tom tat su kien camera hom nay','{"scope":"maintenance"}')
) AS x(intent_name,prompt_text,prompt_norm,meta) ON x.intent_name=i.intent_name
ON CONFLICT (intent_id,prompt_text) DO NOTHING;

INSERT INTO answers (intent_id,answer_text,answer_type,source_note,is_active)
SELECT i.intent_id,x.answer_text,'default','demo_seed',TRUE
FROM intents i JOIN (VALUES
('customer_greeting','Xin chào, tôi là Sunybot. Tôi có thể hỗ trợ hướng dẫn và thông tin an toàn thang máy.'),
('customer_safety','Hãy giữ bình tĩnh, dùng nút SOS hoặc intercom và không tự cạy cửa khi cabin chưa ở vị trí an toàn.'),
('maintenance_cv_summary','Tôi sẽ đọc dữ liệu CV đã ghi nhận thay vì tự suy đoán từ mô hình ngôn ngữ.')
) AS x(intent_name,answer_text) ON x.intent_name=i.intent_name
WHERE NOT EXISTS (SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id AND a.answer_text=x.answer_text);
