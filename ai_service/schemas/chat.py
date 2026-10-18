"""schemas 层：chat 接口的请求/响应模型。"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(description="消息角色：user / assistant")
    content: str = Field(description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(description="用户输入")
    session_id: str | None = Field(default=None, description="会话 ID（预留多轮）")
    history: list[ChatMessage] = Field(
        default_factory=list, description="历史消息，前端可选传入"
    )


class ToolCallRecord(BaseModel):
    tool: str
    args: dict
    result_preview: str = Field(description="工具返回内容预览（截断）")


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    model: str


class HealthResponse(BaseModel):
    status: str
    model: str
    web_search: bool = Field(description="联网检索是否开启")
    tools: list[str]
