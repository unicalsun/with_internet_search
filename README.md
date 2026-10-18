# Internet Search Agent

基于 **FastAPI + LangGraph + FastMCP** 的联网查询 Agent：LLM 通过 ReAct 循环编排联网工具（搜索 / 网页抓取），回答最新问题并附引用来源。当前提供命令行入口，HTTP 接口已预留，可直接对接 WebUI / 飞书机器人。

## 功能特性

- **Agent 编排**：LangGraph 实现 ReAct 循环（模型思考 → 工具调用 → 结果回填 → 再思考），自动决定是否联网、搜什么、抓哪个页面
- **MCP 工具网关**：FastMCP 独立服务，内置两个联网工具，与 AI service 通过 MCP 协议（streamable HTTP）解耦，新增工具无需改 agent 代码
- **模型可配置**：DeepSeek API，模型名 / 温度 / base_url / API Key 全部经 `.env` 注入，默认 `deepseek-v4-flash`
- **权限校验**：`X-API-Key` 请求头认证，多 Key 支持，未配置时为本地开发模式
- **结果整合**：响应包含最终回答 + 全程工具调用轨迹（工具名、参数、结果预览），便于前端展示与审计
- **联网检索开关**：`ENABLE_WEB_SEARCH`（默认开）或启动参数 `--no-web-search` 可关闭，关闭后不连接 MCP 网关，纯本地问答
- **多端复用**：CLI / WebUI / 飞书机器人共用同一个 `POST /v1/chat` 接口

## 系统架构

```
┌─────────────┐   HTTP    ┌──────────────────────────────┐   MCP    ┌─────────────────┐
│  表现层      │ ────────► │  AI service (FastAPI)        │ ───────► │  MCP 网关        │
│  cli/chat   │ /v1/chat  │  ├ api/      路由与鉴权       │ stream-  │  (FastMCP)      │
│  (WebUI/飞书)│           │  ├ core/     配置/安全/图编排  │ able     │  ├ search_web    │
│  预留        │           │  ├ services/ 会话/结果整合    │ HTTP     │  └ fetch_web_page│
└─────────────┘           │  └ schemas/  数据模型        │ :8001/mcp└─────────────────┘
                          └──────────────────────────────┘
                                    │  DeepSeek API
                                    ▼
```

**请求链路**：CLI/WebUI → AI service（API Key 校验）→ LangGraph agent 循环 → 绑定的 MCP 工具 → MCP 网关执行（DuckDuckGo 搜索 / 网页抓取）→ 结果回填模型 → 整合回答与工具轨迹 → 返回。

## 项目结构

```
with_internet_search/
├── ai_service/                  # AI service（FastAPI + LangGraph）
│   ├── main.py                  #   入口：lifespan 加载 MCP 工具、构建图
│   ├── api/chat.py              #   POST /v1/chat
│   ├── core/
│   │   ├── config.py            #   .env 配置（pydantic-settings）
│   │   ├── security.py          #   X-API-Key 权限校验
│   │   └── graph.py             #   LangGraph ReAct 图
│   ├── services/agent_service.py#   会话历史、结果整合、工具轨迹提取
│   └── schemas/chat.py          #   请求/响应模型
├── mcp_gateway/                 # MCP 工具网关（FastMCP）
│   ├── main.py                  #   工具注册，streamable HTTP :8001
│   └── tools/
│       ├── web_search.py        #   DuckDuckGo 搜索（免 API key）
│       └── fetch_url.py         #   网页抓取 + 正文提取
├── cli/chat.py                  # 命令行聊天客户端（rich 渲染）
├── .env.example                 # 配置模板
├── .gitignore
├── agents.md                    # 架构与协作约定
├── changelog.md                 # 变更记录
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env`，至少填入 `DEEPSEEK_API_KEY`：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（必填） | — |
| `DEEPSEEK_BASE_URL` | 模型 API 地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名 | `deepseek-v4-flash` |
| `LLM_TEMPERATURE` | 温度 | `0.1` |
| `LLM_MAX_TOKENS` | 单次回复最大 token 数 | `2048` |
| `VALID_API_KEYS` | 逗号分隔的合法 API Key；留空 = 开发模式不校验 | `dev-api-key` |
| `ENABLE_WEB_SEARCH` | 联网检索开关；`false` 时不加载 MCP 工具，纯本地问答 | `true` |
| `MAX_AGENT_TURNS` | agent 最大工具调研轮次；超限返回阶段性回答 | `16` |
| `MCP_GATEWAY_HOST` / `PORT` | 网关监听地址/端口 | `0.0.0.0` / `8001` |
| `MCP_GATEWAY_URL` | AI service 连网关的地址 | `http://127.0.0.1:8001/mcp` |
| `AI_SERVICE_HOST` / `PORT` | AI service 监听地址/端口 | `0.0.0.0` / `8000` |

> 注意：`MCP_GATEWAY_URL` 是**客户端连接地址**，不能写 `0.0.0.0`（Windows 下会连接失败），用 `127.0.0.1` 或 `localhost`。修改 `.env` 后需重启对应服务才生效。

### 3. 启动（三个终端）

```bash
# 终端 A：MCP 网关（关闭联网检索时可不启动）
python -m mcp_gateway.main

# 终端 B：AI service（需在网关之后启动）
python -m ai_service.main                  # 联网检索（默认）
python -m ai_service.main --no-web-search  # 关闭联网检索，纯本地问答

# 终端 C：命令行聊天
python cli\chat.py        # Windows
python -m cli.chat        # 跨平台
```

示例对话：

```
你: 请搜索并告诉我 LangGraph 最新版本号是多少，附来源链接

[工具调用]
• search_web(query='LangGraph latest version release', max_results=5)
• fetch_web_page(url='https://pypi.org/project/langgraph/', max_length=3000)

[回答]
最新版本为 langgraph 1.2.15（2026-10-12）...
来源: https://pypi.org/project/langgraph/
```

## API 接口

### `POST /v1/chat`

Header：`X-API-Key: <key>`（开发模式可省略）

请求体：

```json
{
  "message": "今天上海的天气如何？",
  "session_id": null,
  "history": []
}
```

响应：

```json
{
  "answer": "根据搜索结果...",
  "session_id": "a1b2c3d4e5f6",
  "tool_calls": [
    {
      "tool": "search_web",
      "args": {"query": "上海 天气", "max_results": 5},
      "result_preview": "[{\"title\": ...}]"
    }
  ],
  "model": "deepseek-v4-flash"
}
```

- `session_id`：首次返回新 ID，后续请求携带即可多轮对话（服务端内存保存，重启即清空）
- `history`：可选，首次请求时可直接传入历史消息 `[{"role": "user"|"assistant", "content": "..."}]`

### `GET /health`

```json
{"status": "ok", "model": "deepseek-v4-flash", "web_search": true, "tools": ["fetch_web_page", "search_web"]}
```

## MCP 工具

网关以 streamable HTTP 暴露在 `http://127.0.0.1:8001/mcp`，任何 MCP 客户端均可接入：

| 工具 | 参数 | 说明 |
|---|---|---|
| `search_web` | `query`, `max_results`(1-20, 默认5) | DuckDuckGo 搜索，返回标题/URL/摘要；限流或空结果时返回可读说明 |
| `fetch_web_page` | `url`, `max_length`(默认4000) | 抓取网页并提取正文纯文本（去除脚本/样式，超长截断）；HTTP 错误/网络异常时返回可读说明 |

## 扩展指引

- **新增工具**：在 `mcp_gateway/tools/` 实现函数，在 `mcp_gateway/main.py` 用 `@mcp.tool` 注册，重启网关即可——AI service 启动时自动发现，无需改 agent 代码
- **接入 WebUI / 飞书机器人**：直接调用 `POST /v1/chat`（鉴权 + 结果轨迹字段已就绪）；飞书回调场景可在此基础上加异步任务与 webhook 路由
- **会话持久化**：`AgentService._sessions` 目前为进程内存，可换 SQLAlchemy 落库

## 常见问题

| 现象 | 原因与解决 |
|---|---|
| CLI 报 401 | `X-API-Key` 与 `.env` 中 `VALID_API_KEYS` 不匹配；CLI 默认读 `VALID_API_KEYS` 第一个值 |
| CLI 报 502 | 模型调用失败：检查 `DEEPSEEK_API_KEY` / `LLM_MODEL`；**改 `.env` 后必须重启 AI service** |
| AI service 启动失败 `ConnectError` | MCP 网关未启动，或 `MCP_GATEWAY_URL` 误写成 `0.0.0.0`；若已关闭联网检索（`ENABLE_WEB_SEARCH=false` / `--no-web-search`）则无需启动网关 |
| 搜索偶发"无结果" | DuckDuckGo 偶发限流，agent 会自动换词重试；持续失败可稍后再试 |
| 回答末尾出现"已达最大工具轮次" | 调研未在 `MAX_AGENT_TURNS`（默认 16）轮内完成：问题拆小分次问，或增大该配置后重启 |
| 端口被占用 | 8000/8001 已有旧进程：`netstat -ano | findstr :8000` 后结束对应 PID |

## 技术栈

FastAPI · LangGraph · langchain-deepseek · langchain-mcp-adapters · FastMCP · DuckDuckGo (ddgs) · httpx + BeautifulSoup · rich

## 相关文档

- [agents.md](agents.md) — 架构分层与协作约定
- [changelog.md](changelog.md) — 版本变更记录
