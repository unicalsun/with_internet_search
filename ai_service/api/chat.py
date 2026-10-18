"""api 层：HTTP 路由（WebUI / 飞书机器人后续复用此接口）。"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from ai_service.core.security import verify_api_key
from ai_service.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger("ai_service.api")

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    _: str = Depends(verify_api_key),
) -> ChatResponse:
    """统一的对话入口：WebUI、飞书机器人、CLI 都走这里。"""
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message 不能为空")

    service = request.app.state.agent_service
    settings = request.app.state.settings

    try:
        answer, session_id, tool_calls = await service.chat(
            message=req.message,
            session_id=req.session_id,
            history=req.history,
        )
    except Exception:
        logger.exception("agent 运行失败")
        raise HTTPException(
            status_code=502,
            detail="模型调用失败，请检查 .env 中 DEEPSEEK_API_KEY / LLM_MODEL 配置",
        )

    return ChatResponse(
        answer=answer,
        session_id=session_id,
        tool_calls=tool_calls,
        model=settings.llm_model,
    )
