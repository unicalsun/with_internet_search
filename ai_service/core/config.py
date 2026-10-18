"""应用配置：从 .env 读取，LLM 信息可自定义。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # AI Service
    valid_api_keys: str = ""
    ai_service_host: str = "127.0.0.1"
    ai_service_port: int = 8000
    max_agent_turns: int = 16
    # 联网检索开关：true 时启动加载 MCP 工具；false 时纯本地问答（也可用启动参数 --no-web-search 关闭）
    enable_web_search: bool = True

    # MCP Gateway
    mcp_gateway_url: str = "http://127.0.0.1:8001/mcp"

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.valid_api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
