"""权限校验：API Key 认证依赖。

开发模式：VALID_API_KEYS 为空时放行（仅限本地调试）。
后续接入飞书/WebUI 时，可在此扩展 OAuth、租户隔离等校验逻辑。
"""

import secrets

from fastapi import Header, HTTPException, status

from ai_service.core.config import get_settings


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """校验请求头 X-API-Key，返回认证身份。"""
    settings = get_settings()
    valid_keys = settings.api_key_list

    if not valid_keys:
        # 未配置 key：本地开发模式
        return "local-dev"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 X-API-Key 请求头",
        )

    for key in valid_keys:
        if secrets.compare_digest(x_api_key, key):
            return "api-key-user"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API Key 无效",
    )
