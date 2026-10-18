"""fetch_url 工具：抓取网页并提取纯文本。"""

import httpx
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def fetch_url(url: str, max_length: int = 4000) -> str:
    """抓取 URL 并返回正文纯文本（去除脚本/样式，超长截断）。失败返回可读说明，便于 agent 换来源。"""
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return (
            f"抓取失败：HTTP {e.response.status_code} {e.response.reason_phrase}"
            f"（{url}）。该网站可能拒绝自动抓取或需要登录，建议换其他来源"
        )
    except httpx.HTTPError as e:  # 超时、DNS 失败等网络异常
        return f"抓取失败（{type(e).__name__}）: {e}，可稍后重试或换其他来源"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    text = " ".join(soup.get_text(separator=" ", strip=True).split())

    if len(text) > max_length:
        text = text[:max_length] + " ...[truncated]"

    return f"URL: {url}\nTitle: {title}\n\n{text}"
