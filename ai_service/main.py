"""AI service 入口：FastAPI 应用装配。

启动顺序：读配置 → 连接 MCP 网关加载工具 → 构建 LangGraph → 挂载路由。
启动方式:
    python -m ai_service.main                # 联网检索（默认）
    python -m ai_service.main --no-web-search  # 关闭联网检索，纯本地问答
"""

import argparse
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from ai_service.api.chat import router as chat_router
from ai_service.core.config import get_settings
from ai_service.core.graph import build_graph
from ai_service.schemas.chat import HealthResponse
from ai_service.services.agent_service import AgentService

logger = logging.getLogger("ai_service")


async def load_mcp_tools() -> list[BaseTool]:
    """从 MCP 网关加载全部工具（tool 名保持 MCP 侧定义）。"""
    settings = get_settings()
    client = MultiServerMCPClient(
        {
            "gateway": {
                "transport": "streamable_http",
                "url": settings.mcp_gateway_url,
            }
        }
    )
    return await client.get_tools()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.deepseek_api_key:
        logger.warning("DEEPSEEK_API_KEY 未配置，模型调用将失败")

    if settings.enable_web_search:
        tools = await load_mcp_tools()
        logger.info("已从 MCP 网关加载工具: %s", [t.name for t in tools])
    else:
        tools = []
        logger.info("联网检索已关闭（ENABLE_WEB_SEARCH=false / --no-web-search），不加载 MCP 工具")

    graph = build_graph(tools)
    app.state.settings = settings
    app.state.agent_service = AgentService(graph, tools)

    yield

    app.state.agent_service = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Internet Search Agent",
        version="0.1.0",
        description="联网检索 AI service：LangGraph 编排 + FastMCP 工具网关",
        lifespan=lifespan,
    )
    app.include_router(chat_router)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        settings = app.state.settings
        service: AgentService = app.state.agent_service
        return HealthResponse(
            status="ok",
            model=settings.llm_model,
            web_search=settings.enable_web_search,
            tools=service.tool_names if service else [],
        )

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI service 启动入口")
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="关闭联网检索（默认开启）",
    )
    args = parser.parse_args()
    if args.no_web_search:
        # 在首次读取配置前写入环境变量（覆盖 .env），lifespan 内生效
        os.environ["ENABLE_WEB_SEARCH"] = "false"

    settings = get_settings()
    uvicorn.run(
        "ai_service.main:app",
        host=settings.ai_service_host,
        port=settings.ai_service_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
