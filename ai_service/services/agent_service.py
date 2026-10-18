"""services 层：agent 运行与结果整合。"""

import uuid

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langgraph.errors import GraphRecursionError

from ai_service.core.config import get_settings
from ai_service.schemas.chat import ChatMessage, ToolCallRecord


class AgentService:
    """封装 agent 图调用、多轮历史、工具轨迹整合。"""

    def __init__(self, graph, tools: list) -> None:
        self._graph = graph
        self._tools = {t.name: t for t in tools}
        # 会话内存（预留：后续可换成数据库持久化）
        self._sessions: dict[str, list[BaseMessage]] = {}

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def _get_history(
        self, session_id: str, history: list[ChatMessage] | None
    ) -> list[BaseMessage]:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            for m in history or []:
                cls = HumanMessage if m.role == "user" else AIMessage
                self._sessions[session_id].append(cls(content=m.content))
        return self._sessions[session_id]

    @staticmethod
    def _extract_tool_calls(messages: list[BaseMessage]) -> list[ToolCallRecord]:
        """从消息轨迹中提取工具调用记录，供前端展示/审计。"""
        records: list[ToolCallRecord] = []
        pending: dict[str, ToolCallRecord] = {}
        for msg in messages:
            for call in getattr(msg, "tool_calls", None) or []:
                rec = ToolCallRecord(
                    tool=call["name"],
                    args=call.get("args", {}),
                    result_preview="",
                )
                key = call.get("id", f"{call['name']}-{len(records)}")
                pending[key] = rec
                records.append(rec)
            if isinstance(msg, ToolMessage):
                rec = pending.get(msg.tool_call_id)
                if rec is not None:
                    content = msg.content
                    if not isinstance(content, str):
                        # 新版 content 可能是内容块列表
                        content = "".join(
                            b.get("text", "") if isinstance(b, dict) else str(b)
                            for b in content
                        )
                    rec.result_preview = content[:500]
        return records

    async def chat(
        self,
        message: str,
        session_id: str | None,
        history: list[ChatMessage] | None = None,
    ) -> tuple[str, str, list[ToolCallRecord]]:
        """运行一次 agent，返回 (answer, session_id, tool_calls)。

        超过最大工具轮次时不再抛错，改为返回阶段性回答并注明截断。
        """
        settings = get_settings()
        sid = session_id or uuid.uuid4().hex[:12]
        messages = self._get_history(sid, history)
        messages.append(HumanMessage(content=message))

        config = {"recursion_limit": settings.max_agent_turns * 2}
        last_state: dict | None = None
        truncated = False
        try:
            # stream_mode="values"：每步 yields 完整状态，异常前已保存最后状态
            async for state in self._graph.astream(
                {"messages": messages}, config=config, stream_mode="values"
            ):
                last_state = state
        except GraphRecursionError:
            truncated = True

        new_messages: list[BaseMessage] = (
            list(last_state["messages"]) if last_state else list(messages)
        )
        tool_calls = self._extract_tool_calls(new_messages)

        if truncated:
            partial = next(
                (
                    m.content
                    for m in reversed(new_messages)
                    if isinstance(m, AIMessage) and m.content
                ),
                "",
            )
            note = f"（已达最大工具轮次 {settings.max_agent_turns}，以下为已收集信息的阶段性回答）"
            answer = (
                f"{partial}\n\n{note}"
                if partial
                else f"（检索已达最大工具轮次 {settings.max_agent_turns}，未能得出结论；建议缩小问题范围重试）"
            )
            new_messages.append(AIMessage(content=answer))
        else:
            answer = next(
                (
                    m.content
                    for m in reversed(new_messages)
                    if isinstance(m, AIMessage) and m.content and not m.tool_calls
                ),
                "（未生成有效回答）",
            )

        # 会话历史只保留 user/assistant 文本，控制上下文长度
        self._sessions[sid] = [
            m
            for m in new_messages
            if isinstance(m, (HumanMessage, AIMessage))
            and not getattr(m, "tool_calls", None)
        ][-20:]

        return answer, sid, tool_calls
