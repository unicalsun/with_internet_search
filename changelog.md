# Changelog

## [Unreleased]

## [0.2.0] - 2026-10-18

### Added
- 联网检索开关（默认开启）：
  - `.env` 配置 `ENABLE_WEB_SEARCH=true|false`；启动参数 `python -m ai_service.main --no-web-search` 临时关闭（环境变量覆盖 `.env`）
  - 关闭时不连接 MCP 网关（网关可不启动），agent 退化为纯本地问答（离线系统提示词，不引导搜索）
  - `GET /health` 响应新增 `web_search` 字段，反映开关状态
- `README.md`：项目说明（功能、架构图、快速开始、API/工具文档、扩展指引、常见问题）

### Changed
- `max_agent_turns` 默认 8 → 16：宽问题（多部分调研 + 并行工具调用）下 8 轮不够用，会撞 `recursion_limit` 被中止
- `agent_service.chat` 改用 `astream(stream_mode="values")` 追踪图状态，超限截断时可提取已收集内容
- 联网检索系统提示词：控制调研轮次、多次失败时基于已有信息直接回答，尽快给出结论
- 配置与文档同步：`.env.example` 新增 `ENABLE_WEB_SEARCH` / `MAX_AGENT_TURNS`；`README.md` 配置表、启动命令、`/health` 示例、常见问题；`agents.md` 设计决策与运行方式

### Fixed
- `/v1/chat` 调研撞轮次上限时返回误导性 502（提示检查 API Key）：`GraphRecursionError` 改在 `agent_service.chat` 内兜底，超限返回已收集信息的阶段性回答并注明截断（HTTP 200）
- `fetch_web_page` 增加容错：HTTP 错误状态码（如 403 反爬拦截）/ 网络异常时返回可读说明，不再抛异常中断 agent 循环（此前 `raise_for_status()` 直接抛 `HTTPStatusError`，agent 无法换来源重试）

### Verified
- 联网检索开关：`--no-web-search` 启动（网关未运行）无连接报错，`/health` 返回 `web_search: false, tools: []`；离线 `/v1/chat` 正常回答且 `tool_calls` 为空
- 轮次截断兜底：强制 `MAX_AGENT_TURNS=2` 触发截断，返回阶段性回答 + 截断说明，不抛错
- 端到端复测「现在黄金金价多少？中国的计价逻辑」：HTTP 200，10 次工具调用，完整回答（此前 502；国际价 / 上金所 Au99.99 / 品牌价 / 计价逻辑）
- `fetch_web_page`：403 站点（如 ir.spacex.com）返回可读说明，正常站点正文提取不受影响

## [0.1.0] - 2026-10-14

### Added
- FastMCP 网关 `mcp_gateway`：`search_web`（DuckDuckGo 搜索）、`fetch_web_page`（网页正文抓取），streamable HTTP 传输
- FastAPI + LangGraph AI service `ai_service`：
  - LangGraph ReAct 编排（agent ↔ tools 循环）
  - ChatDeepSeek 模型调用，模型/温度/base_url 经 `.env` 注入，默认 `deepseek-v4-flash`
  - MCP 工具动态加载与路由
  - X-API-Key 权限校验（预留飞书/WebUI 扩展）
  - 结果整合：回答 + 工具调用轨迹
  - `POST /v1/chat`、`GET /health` 接口
- CLI 聊天客户端 `cli/chat.py`（rich 渲染，走 HTTP 与 WebUI/飞书同接口）
- `agents.md` 架构说明、`.env.example` 配置模板

### Fixed
- fastmcp 3.x 移除了 `FastMCP(host=, port=)` 构造参数，改在 `run(transport="http", host, port)` 传入
- `web_search` 增加容错：ddgs 限流/空结果时返回可读说明，不再抛异常中断 agent 循环
- `/v1/chat` 捕获模型调用异常，返回 502 + 配置提示（此前为裸 500）
- `.env` 配置坑：`MCP_GATEWAY_URL` 是客户端连接地址，不能写 `0.0.0.0`（Windows 连接失败），已在 `.env.example` 注明
- 会话历史过滤对 `HumanMessage` 误访问 `tool_calls` 属性导致 502，改用 `getattr` 兼容
- 工具轨迹预览兼容 `ToolMessage.content` 的内容块列表格式

### Verified
- MCP 网关：`search_web` / `fetch_web_page` 经 MCP 协议（streamable HTTP）加载与调用正常
- AI service：`/health` 正常；无 key / 错 key → 401；配置错误 → 502 提示
- 端到端联网问答通过：agent 多轮 search_web + fetch_web_page，限流自动换词重试，最终带引用回答
