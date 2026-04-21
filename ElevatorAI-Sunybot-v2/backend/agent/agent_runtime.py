import json
import time
import uuid
from typing import Any, Dict, List, Optional

from backend.agent.memory_store import ConversationMemoryStore
from backend.agent.planner import Planner
from backend.agent.safety import SafetyGuardrails
from backend.agent.tool_registry import ToolRegistry
from backend.schemas import Citation, ChatResponse, ToolTrace


class AgentRuntime:
    def __init__(self, tool_registry: ToolRegistry):
        self.tools = tool_registry
        self.memory = ConversationMemoryStore(max_turns=12)
        self.safety = SafetyGuardrails()
        self.planner = Planner()

    def run(
        self,
        message: str,
        session_id: Optional[str] = None,
        scope: str = "customer",
        persona: str = "customer_assistant",
    ) -> Dict[str, Any]:
        session_id = session_id or uuid.uuid4().hex
        user_text = (message or "").strip()
        if not user_text:
            return ChatResponse(
                answer="Bạn vui lòng nhập câu hỏi.",
                source="SYSTEM",
                intent="empty_input",
                confidence=1.0,
                session_id=session_id,
            ).dict()

        self.memory.add_turn(session_id, "user", user_text, metadata={"scope": scope, "persona": persona})
        memory_summary = self.memory.build_summary(session_id)
        precheck = self.safety.precheck(user_text)
        if precheck.get("status") == "blocked":
            answer = precheck.get("answer", "Yêu cầu đã bị chặn bởi guardrail.")
            self.memory.add_turn(session_id, "assistant", answer, metadata={"intent": precheck.get("intent")})
            return ChatResponse(
                answer=answer,
                source="SAFETY",
                intent=precheck.get("intent", "blocked"),
                confidence=1.0,
                session_id=session_id,
                memory_summary=memory_summary,
                status="blocked",
            ).dict()

        plan = self.planner.create_plan(user_text, history=self.memory.get_history(session_id))
        traces: List[ToolTrace] = []
        citations: List[Citation] = []
        tool_results: List[Dict[str, Any]] = []

        if precheck.get("status") == "emergency" and not any(call.tool_name == "get_elevator_status" for call in plan.tool_calls):
            from backend.schemas import ToolCall

            plan.tool_calls.insert(
                0,
                ToolCall(
                    tool_name="get_elevator_status",
                    args={"elevator_id": 1},
                    reason="Bổ sung trạng thái thang máy cho tình huống khẩn cấp",
                ),
            )

        for tool_call in plan.tool_calls:
            if tool_call is None:
                continue
            if not self.safety.allow_tool(tool_call.tool_name):
                traces.append(
                    ToolTrace(
                        tool_name=tool_call.tool_name,
                        args=tool_call.args,
                        status="blocked",
                        summary="Tool bị guardrail chặn.",
                    )
                )
                continue

            started = time.time()
            try:
                args = dict(tool_call.args or {})
                if tool_call.tool_name == "general_llm":
                    args.setdefault("persona", persona)
                result = self.tools.run(tool_call.tool_name, args)
                duration_ms = int((time.time() - started) * 1000)
                traces.append(
                    ToolTrace(
                        tool_name=tool_call.tool_name,
                        args=args,
                        status="ok" if result.get("ok") else "error",
                        duration_ms=duration_ms,
                        summary=(result.get("message") or "")[:220],
                    )
                )
                tool_results.append({"tool": tool_call.tool_name, "result": result})
                for item in result.get("citations", []):
                    citations.append(Citation(**item))
            except Exception as exc:
                duration_ms = int((time.time() - started) * 1000)
                traces.append(
                    ToolTrace(
                        tool_name=tool_call.tool_name,
                        args=tool_call.args,
                        status="error",
                        duration_ms=duration_ms,
                        summary="Tool lỗi: {0}".format(exc),
                    )
                )

        citations = self._dedupe_citations(citations)
        response = self._compose_response(
            user_text=user_text,
            session_id=session_id,
            plan_intent=plan.intent,
            plan_confidence=plan.confidence,
            precheck=precheck,
            tool_results=tool_results,
            traces=traces,
            citations=citations,
            memory_summary=memory_summary,
            persona=persona,
        )
        assistant_meta = self._extract_memory_metadata(response, tool_results)
        self.memory.add_turn(session_id, "assistant", response["answer"], metadata=assistant_meta)
        return response

    def _compose_response(
        self,
        user_text: str,
        session_id: str,
        plan_intent: str,
        plan_confidence: float,
        precheck: Dict[str, str],
        tool_results: List[Dict[str, Any]],
        traces: List[ToolTrace],
        citations: List[Citation],
        memory_summary: str,
        persona: str,
    ) -> Dict[str, Any]:
        source = "AGENT"
        answer = "Sunybot hiện chưa có đủ dữ liệu để trả lời chính xác câu hỏi này."
        requires_human = False
        result_map = {item["tool"]: item["result"] for item in tool_results}

        if plan_intent == "employee_lookup":
            employee_result = result_map.get("employee_lookup", {})
            if employee_result.get("ok"):
                answer = employee_result.get("message", answer)
                source = employee_result.get("source", "EMPLOYEE")
            else:
                answer = employee_result.get("message", "Không tìm thấy nhân viên phù hợp.")
                source = "EMPLOYEE"

        elif plan_intent == "elevator_status":
            status_result = result_map.get("get_elevator_status", {})
            answer = status_result.get("message", answer)
            source = status_result.get("source", "ELEVATOR_STATUS")

        elif plan_intent == "call_elevator":
            call_result = result_map.get("call_elevator", {})
            answer = call_result.get("message", answer)
            source = call_result.get("source", "COMMAND")

        elif plan_intent == "knowledge_lookup":
            kb_result = result_map.get("kb_search", {})
            context_blocks = kb_result.get("passages", []) if kb_result.get("ok") else []
            llm_result = self.tools.run(
                "general_llm",
                {
                    "query": user_text,
                    "context_blocks": context_blocks,
                    "memory_summary": memory_summary,
                    "intent_hint": "knowledge_lookup",
                    "persona": persona,
                },
            )
            traces.append(
                ToolTrace(
                    tool_name="general_llm",
                    args={"query": user_text, "persona": persona},
                    status="ok" if llm_result.get("ok") else "error",
                    summary=(llm_result.get("message") or "")[:220],
                )
            )
            for item in llm_result.get("citations", []):
                citations.append(Citation(**item))
            if llm_result.get("ok"):
                answer = llm_result.get("message") or kb_result.get("message", answer)
                source = "AGENT"
            else:
                answer = kb_result.get("message", answer)
                source = kb_result.get("source", "KB")

        else:
            llm_result = result_map.get("general_llm", {})
            answer = llm_result.get("message", answer)
            source = llm_result.get("source", "LLM")

        if precheck.get("status") == "emergency":
            status_result = result_map.get("get_elevator_status", {})
            suffix = status_result.get("message", "")
            answer = "{0} {1}".format(precheck.get("answer", ""), suffix).strip()
            source = "SAFETY"
            requires_human = True

        return ChatResponse(
            answer=answer,
            source=source,
            intent=plan_intent if precheck.get("status") == "ok" else precheck.get("intent"),
            confidence=round(float(plan_confidence), 3),
            session_id=session_id,
            tool_trace=traces,
            citations=self._dedupe_citations(citations),
            memory_summary=self.memory.build_summary(session_id),
            requires_human=requires_human,
            status="ok" if precheck.get("status") in [None, "ok", "emergency"] else precheck.get("status", "ok"),
        ).dict()

    def _dedupe_citations(self, citations: List[Citation]) -> List[Citation]:
        seen = set()
        deduped = []
        for item in citations:
            key = (item.source, item.content)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _extract_memory_metadata(self, response: Dict[str, Any], tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        meta: Dict[str, Any] = {"intent": response.get("intent")}
        result_map = {item["tool"]: item["result"] for item in tool_results}

        emp = result_map.get("employee_lookup", {}).get("employee") or {}
        if emp.get("employee_code"):
            meta["employee_code"] = emp.get("employee_code")

        status = result_map.get("get_elevator_status", {}).get("status_data") or {}
        if status.get("elevator_id") is not None:
            meta["elevator_id"] = status.get("elevator_id")

        command = result_map.get("call_elevator", {}).get("command") or {}
        if command.get("elevator_id") is not None:
            meta["elevator_id"] = command.get("elevator_id")
        if command.get("from_floor") is not None:
            meta["from_floor"] = command.get("from_floor")
        if command.get("target_floor") is not None:
            meta["target_floor"] = command.get("target_floor")

        return meta

    def serialize_trace(self, traces: List[ToolTrace]) -> str:
        return json.dumps([trace.dict() for trace in traces], ensure_ascii=False)
