"""CLI 聊天客户端：通过 HTTP 调用 AI service（预留 WebUI/飞书同款接口）。

用法:
    python -m cli.chat
"""

import os
import sys

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv()

console = Console()

SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("CLI_API_KEY", os.getenv("VALID_API_KEYS", "").split(",")[0].strip())


def send(message: str, session_id: str | None) -> dict:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    resp = httpx.post(
        f"{SERVICE_URL}/v1/chat", json=payload, headers=headers, timeout=120
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]联网查询 Agent CLI[/bold cyan]\n"
            f"服务地址: {SERVICE_URL}\n"
            "输入问题开始对话；输入 exit / quit 退出",
            border_style="cyan",
        )
    )
    session_id: str | None = None

    while True:
        try:
            message = Prompt.ask("\n[bold green]你[/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            break

        with console.status("[dim]思考中...[/dim]"):
            try:
                data = send(message, session_id)
            except httpx.HTTPStatusError as e:
                console.print(f"[red]请求失败: {e.response.status_code} {e.response.text}[/red]")
                continue
            except httpx.HTTPError as e:
                console.print(f"[red]无法连接 AI service: {e}[/red]")
                continue

        session_id = data["session_id"]

        tool_calls = data.get("tool_calls") or []
        if tool_calls:
            lines = []
            for tc in tool_calls:
                args = ", ".join(f"{k}={v!r}" for k, v in tc["args"].items())
                lines.append(f"• [yellow]{tc['tool']}[/yellow]({args})")
            console.print(Panel("\n".join(lines), title="工具调用", border_style="yellow"))

        console.print(Panel(Markdown(data["answer"]), title=f"回答 · {data['model']}", border_style="blue"))

    console.print("[dim]再见。[/dim]")


if __name__ == "__main__":
    sys.exit(main())
