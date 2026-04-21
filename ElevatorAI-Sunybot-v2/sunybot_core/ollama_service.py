# backend/ollama_service.py
import os
import time
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:1.5b-instruct")

FALLBACK_TEXT = "Sunybot hiện không thể trả lời câu hỏi này."

class OllamaService:

    def _build_prompt(self, user_text: str) -> str:
        # PROMPT CỰC NGẮN – TỐI ƯU TỐC ĐỘ
        return (
            "Bạn là Sunybot, chatbot thang máy. "
            "Trả lời ngắn gọn bằng tiếng Việt (1 câu).\n"
            f"Câu hỏi: {user_text}\n"
            "Trả lời:"
        )

    def generate(
        self,
        user_text: str,
        connect_timeout: int = 3,
        read_timeout: int = 40,
        retries: int = 0
    ) -> str:

        url = f"{OLLAMA_HOST}/api/generate"
        prompt = self._build_prompt(user_text)

        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 35,   # ⬅ GIẢM MẠNH #phần điều chỉnh chiều dài của token 
                "num_ctx": 512,
                "temperature": 0.3,
                "top_p": 0.7
            }
        }

        try:
            r = requests.post(
                url,
                json=payload,
                timeout=(connect_timeout, read_timeout)
            )

            if r.status_code != 200:
                return FALLBACK_TEXT

            data = r.json()
            ans = (data.get("response") or "").strip()

            if not ans:
                return FALLBACK_TEXT

            # CẮT PHÒNG HỜ – 1 CÂU
            ans = ans.replace("\n", " ")
            if "." in ans:
                ans = ans.split(".")[0] + "."

            return ans

        except Exception as e:
            print(f"[OLLAMA_ERR] {e}")
            return FALLBACK_TEXT

    def chat(self, user_text: str, timeout_sec: int = 40) -> str:
        return self.generate(user_text, read_timeout=timeout_sec)

