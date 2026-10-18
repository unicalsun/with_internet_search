"""LangGraph 编排：ReAct 循环（agent ↔ tools）。

- 模型调用：ChatDeepSeek，模型/温度等从 .env 注入
- 工具路由：启动时从 MCP 网关加载，绑定给模型；有 tool_call 进 ToolNode，
  否则整合结果返回
"""

from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from ai_service.core.config import get_settings

SYSTEM_PROMPT = (
    "你是一个联网检索助手。回答问题前，如果需要最新信息，"
    "先用 search_web 搜索，必要时用 fetch_web_page 抓取原文；"
    "控制调研轮次，拿到关键信息后尽快给出结论；"
    "若多次搜索或抓取失败，基于已有信息直接回答，不要反复重试同一来源。"
    "回答时给出结论并附上引用的 URL；无法确认的信息要明确说明。"
)

OFFLINE_SYSTEM_PROMPT = (
    "你是一个问答助手。根据已有知识直接回答问题；"
    "无法确认的信息要明确说明，不要编造。"
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _build_llm() -> ChatDeepSeek:
    s = get_settings()
    return ChatDeepSeek(
        model=s.llm_model,
        temperature=s.llm_temperature,
        max_tokens=s.llm_max_tokens,
        api_key=s.deepseek_api_key,
        base_url=s.deepseek_base_url,
    )


def build_graph(tools: list[BaseTool]):
    """由工具列表构建 LangGraph agent 图；无工具时退化为纯问答（离线模式）。"""
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)
    system_prompt = SYSTEM_PROMPT if tools else OFFLINE_SYSTEM_PROMPT

    async def agent_node(state: AgentState) -> dict:
        response = await llm_with_tools.ainvoke(
            [SystemMessage(content=system_prompt), *state["messages"]]
        )
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        if not tools:
            return "end"
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return "end"

    graph = (
        StateGraph(AgentState)
        .add_node("agent", agent_node)
        .add_node("tools", tool_node)
        .add_edge(START, "agent")
        .add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", "end": END},
        )
        .add_edge("tools", "agent")
    )
    return graph.compile()
