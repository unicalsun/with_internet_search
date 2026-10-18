"""web_search 工具：基于 DuckDuckGo 的免 key 网页搜索。"""

from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """搜索网络，返回标题、链接、摘要列表。失败/空结果返回可读说明，便于 agent 自行调整。"""
    max_results = max(1, min(max_results, 20))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:  # 限流、网络异常等
        return [{"title": "", "url": "", "snippet": f"搜索失败（{type(e).__name__}）: {e}，可换关键词重试"}]

    if not results:
        return [{"title": "", "url": "", "snippet": "无搜索结果，可尝试更换关键词"}]

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", r.get("url", "")),
            "snippet": r.get("body", r.get("snippet", "")),
        }
        for r in results
    ]
