# Step 1 - Chuan hoa database va embedding cho Jetson Nano

## 1) Backup database truoc khi doi schema
```bash
pg_dump -h 127.0.0.1 -U postgres -d elevator_ai_pg > backup_before_step1.sql
```

## 2) Nap schema moi
```bash
psql -h 127.0.0.1 -U postgres -d elevator_ai_pg -f /mnt/data/schema_pg_step1.sql
```

## 3) Seed lai data co cau truc
```bash
psql -h 127.0.0.1 -U postgres -d elevator_ai_pg -f /mnt/data/seed_pg_step1.sql
```

## 4) Build embeddings
Khuyen nghi cho Jetson Nano:
```bash
export EMBED_MODEL=nomic-embed-text
export EMBED_DIM=768
export EMBED_BATCH_LIMIT=0
export EMBED_FORCE_REBUILD=1
export EMBED_TEXT_MODE=prompt
export EMBED_SLEEP_MS=150
python3 /mnt/data/build_embeddings_step1.py
```

Neu muon rebuild nhanh hon va may van on:
```bash
export EMBED_SLEEP_MS=0
python3 /mnt/data/build_embeddings_step1.py
```

## 5) Chay test co ban
```bash
pytest /mnt/data/test_chatbot_step1.py -q
```

## 6) Kiem tra nhanh trong SQL
```sql
SELECT intent_name, domain, priority FROM intents ORDER BY priority, intent_name;
SELECT COUNT(*) AS prompt_count FROM prompts;
SELECT COUNT(*) AS employee_count FROM employees;
SELECT prompt_id, prompt_text, embedding_model FROM prompts ORDER BY prompt_id LIMIT 10;
```

## 7) Luu y Jetson Nano
- Khong nen nhap qua nhieu tai lieu th raw o Step 1.
- Chi embed prompts / paraphrase, khong embed bang employees.
- Bat dau voi seed 50-80 prompts la hop ly.
- Neu CPU nong, dat `EMBED_SLEEP_MS=150` hoac `250`.
