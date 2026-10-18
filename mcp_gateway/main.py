"""MCP 网关入口：注册 web_search / fetch_url，以 streamable HTTP 对外提供。

启动方式:
    python -m mcp_gateway.main
默认监听 http://127.0.0.1:8001/mcp
"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from mcp_gateway.tools.fetch_url import fetch_url
from mcp_gateway.tools.web_search import web_search

load_dotenv()

HOST = os.getenv("MCP_GATEWAY_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_GATEWAY_PORT", "8001"))
# fastmcp 3.x 通过环境变量配置 HTTP 监听地址
os.environ["FASTMCP_HOST"] = HOST
os.environ["FASTMCP_PORT"] = str(PORT)

mcp = FastMCP(
    name="internet-search-gateway",
    instructions="联网检索网关：提供网页搜索与网页正文抓取能力。",
)


@mcp.tool
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """搜索互联网，返回与 query 相关的结果列表（标题、URL、摘要）。

    Args:
        query: 搜索关键词
        max_results: 返回条数，默认 5，最大 20
    """
    return web_search(query, max_results)


@mcp.tool
def fetch_web_page(url: str, max_length: int = 4000) -> str:
    """抓取指定 URL 的网页内容，返回标题与正文纯文本。

    Args:
        url: 完整的 http/https 地址
        max_length: 正文最大长度（字符），默认 4000
    """
    return fetch_url(url, max_length)


def main() -> None:
    mcp.run(transport="http", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
