from functools import lru_cache
from typing import Any, Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.utils.project import get_env_files, get_project_version

__all__ = ['settings']


class Settings(BaseSettings):
    """全局应用配置."""

    model_config = SettingsConfigDict(
        env_file=get_env_files(),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore',
    )

    # ============== 基础环境 ==============
    ENVIRONMENT: Literal['development', 'test', 'production'] = 'development'

    FASTAPI_TITLE: str = 'FastAPI Services'
    FASTAPI_VERSION: str = Field(default_factory=get_project_version)
    FASTAPI_DESCRIPTION: str = '基于 FastAPI 构建的后端服务架构模板'

    FASTAPI_DOCS_URL: str | None = '/docs'
    FASTAPI_REDOC_URL: str | None = '/redoc'
    FASTAPI_OPENAPI_URL: str | None = '/openapi.json'
    FASTAPI_STATIC_FILES: bool = False

    # Swagger UI 文档交互参数
    FASTAPI_SWAGGER_UI_PARAMETERS: dict[str, Any] = Field(
        default_factory=lambda: {
            'docExpansion': 'list',
            'persistAuthorization': True,
            'displayRequestDuration': True,
        }
    )

    # ============== 时间与时区 ==============
    DATETIME_FORMAT: str = '%Y-%m-%dT%H:%M:%S'
    DATETIME_TIMEZONE: str = 'Asia/Shanghai'

    # ============== 多租户与 Schema 隔离配置 ==============
    TENANT_ENABLED: bool = True  # 是否启用多租户模式
    TENANT_DEFAULT_SCHEMA: str = 'public'  # 默认公共 Schema 名称（单租户或公共表所在）
    TENANT_HEADER_KEY: str = 'X-Tenant-ID'  # 请求头租户标识
    TENANT_SCHEMA_PREFIX: str = 'tenant_'  # 租户物理 Schema 的命名前缀
    TENANT_SCHEMA_PATTERN: str = r'^[a-z][a-z0-9_]{1,62}$'  # 租户物理 Schema 命名

    # ============== PostgreSQL 数据库 ==============
    DATABASE_URL: str = 'postgresql+asyncpg://postgres:123456@127.0.0.1:5432/fs_db'
    DATABASE_ECHO: bool = False  # 是否在日志中输出执行的 SQL 语句
    DATABASE_ECHO_POOL: bool | Literal['debug'] = False  # 是否在日志中输出数据库连接池的调试信息

    # 连接池配置
    DATABASE_POOL_SIZE: int = 10  # 常驻连接数
    DATABASE_MAX_OVERFLOW: int = 20  # 超载时的连接上限
    DATABASE_POOL_TIMEOUT: int = 30  # 等待超时（秒）
    DATABASE_POOL_RECYCLE: int = 3600  # 最大存活时间（秒）超时回收（-1 为不回收）
    DATABASE_POOL_PRE_PING: bool = True
    DATABASE_POOL_USE_LIFO: bool = False  # 是否使用 LIFO 策略优先复用活跃连接

    # ============== Redis 缓存 ==============
    REDIS_URL: str = 'redis://127.0.0.1:6379/0'  # Redis 缓存连接 URL
    REDIS_KEY_PREFIX: str = 'fs:'  # 统一 Key 前缀
    REDIS_TIMEOUT: int = 5  # 连接与操作超时时间（秒）
    REDIS_MAX_CONNECTIONS: int = 50  # 连接池最大连接数

    # ============== Celery 异步任务与定时调度 ==============
    CELERY_BROKER_URL: str = 'amqp://user:pass@localhost:5672//'  # 消息代理 Broker URL
    CELERY_BACKEND_URL: str = 'redis://127.0.0.1:6379/2'  # 结果存储 Backend URL
    CELERY_TASK_DEFAULT_QUEUE: str = 'fs_tasks'  # 默认任务队列名称
    CELERY_TIMEZONE: str = 'Asia/Shanghai'  # Celery 时区

    # ============== 限流配置 ==============
    RATE_LIMIT_ENABLED: bool = True  # 是否启用全局限流
    RATE_LIMIT_DEFAULT_RATE: int = 60  # 默认限流频次
    RATE_LIMIT_DEFAULT_PERIOD: int = 60  # 默认限流周期（秒）
    RATE_LIMIT_REDIS_URL: str | None = None  # 限流 Redis URL

    # ============== 实时通信 ==============
    SOCKETIO_PATH: str = '/ws'  # 挂载路径
    SOCKETIO_REDIS_URL: str | None = None  # 跨进程广播 Redis URL
    SOCKETIO_CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ['*'])  # 允许跨域来源
    SOCKETIO_ASYNC_MODE: str = 'asgi'  # 异步运行

    # ============== IP 属地解析 ==============
    IP2REGION_ENABLED: bool = True  # 是否启用 IP 属地解析

    # ============== 中间件与跨域访问 ==============
    MIDDLEWARE_CORS: bool = True  # 是否启用
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ['*'])  # 允许跨域请求地址列表
    CORS_EXPOSE_HEADERS: list[str] = Field(default_factory=lambda: ['*'])  # 允许客户端访问的响应头
    CORS_ALLOW_CREDENTIALS: bool = True  # 是否支持跨域携带 Cookie / 认证凭据
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ['*'])  # 允许跨域的 HTTP 请求方法列表
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ['*'])  # 允许跨域请求携带的请求头列表

    # ============== 请求上下文与链路追踪 ==============
    TRACE_ID_HEADER: str = 'X-Request-ID'
    TRACE_ID_LOG_DEFAULT: str = '-'

    # ============== 请求访问日志、敏感数据脱敏 ==============
    REQUEST_LOG_ENABLE: bool = True
    REQUEST_LOG_EXCLUDE_PATHS: list[str] = Field(
        default_factory=lambda: [
            '/favicon.ico',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/health',
            '/admin/health',
            '/api/health',
        ]
    )  # 不记录日志地址列表
    REQUEST_LOG_ENCRYPT_FIELDS: list[str] = Field(
        default_factory=lambda: [
            'password',
            'old_password',
            'new_password',
            'confirm_password',
            'token',
            'access_token',
            'refresh_token',
            'secret',
        ]
    )  # 脱敏加密字段

    # ============== 日志系统配置（Loguru） ==============
    LOG_CONSOLE_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'  # 控制台日志级别
    LOG_FILE_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'  # 文件记录日志级别
    LOG_ACCESS_FILENAME: str = 'access.log'
    LOG_ERROR_FILENAME: str = 'error.log'
    LOG_RETENTION: str = '30 days'  # 文件保留周期（过期自动清理）
    LOG_ROTATION: str = '00:00'  # 日志切分滚动周期（每日零点自动切分）
    LOG_STD_FORMAT: str = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | '
        '<lvl>{level: <8}</> | '
        '<cyan>{extra[request_id]}</> | '
        '<lvl>{message}</>'
    )  # 日志格式模板

    # ============== 验证码配置 ==============
    CAPTCHA_EXPIRE_SECONDS: int = 60 * 5  # 验证码有效时间（5 分钟）

    # ============== 安全凭证与令牌配置（JWT & Token） ==============
    TOKEN_SECRET_KEY: str = 'changeme_in_production_32b_secret_key'  # 秘钥，可通过 os.urandom(32).hex() 生成
    TOKEN_ALGORITHM: str = 'HS256'  # 签名加密算法
    TOKEN_EXPIRE_SECONDS: int = 86400 * 3  # Access Token 默认有效期（3 天）
    TOKEN_REFRESH_EXPIRE_SECONDS: int = 86400 * 7  # Refresh Token 默认有效期（7 天）
    TOKEN_ISSUER: str = 'fs'  # JWT 签发者
    TOKEN_AUDIENCE_ADMIN: str = 'fs:admin'  # 管理端 JWT 受众标识
    TOKEN_AUDIENCE_CLIENT: str = 'fs:client'  # 客户端 JWT 受众标识

    # ============== 安全 Cookie 配置 ==============
    COOKIE_REFRESH_TOKEN_KEY: str = 'fs_refresh_token'
    COOKIE_SECURE: bool = False
    COOKIE_HTTPONLY: bool = True  # 是否禁止客户端 JavaScript 读取
    COOKIE_SAMESITE: Literal['lax', 'strict', 'none'] = 'lax'  # SameSite 策略
    COOKIE_DOMAIN: str | None = None  # Cookie 作用域域名（如 .example.com）
    COOKIE_PATH: str = '/'  # Cookie 生效路径

    @model_validator(mode='after')
    def validate_environment_settings(self) -> Self:
        """环境安全与合理性校验."""
        self.FASTAPI_VERSION = get_project_version()

        # 复用主 REDIS_URL
        if not self.RATE_LIMIT_REDIS_URL:
            self.RATE_LIMIT_REDIS_URL = self.REDIS_URL
        if not self.SOCKETIO_REDIS_URL:
            self.SOCKETIO_REDIS_URL = self.REDIS_URL

        if self.ENVIRONMENT == 'production':
            # 生产环境默认隐藏 Swagger / Redoc / OpenAPI Schema
            self.FASTAPI_DOCS_URL = None
            self.FASTAPI_REDOC_URL = None
            self.FASTAPI_OPENAPI_URL = None

            # 生产环境 CORS 安全防范（禁止 credentials=True 与通配符 origins 同时存在）
            if self.MIDDLEWARE_CORS and self.CORS_ALLOW_CREDENTIALS and '*' in self.CORS_ALLOWED_ORIGINS:
                raise ValueError(
                    '生产环境下启用 CORS_ALLOW_CREDENTIALS 时，CORS_ALLOWED_ORIGINS 不能包含通配符 "*"，'
                    '请配置明确的前端域名白名单。'
                )

            # 生产环境 Cookie 强制启用 Secure
            self.COOKIE_SECURE = True

        return self


@lru_cache
def get_settings() -> Settings:
    """全局配置单例."""
    return Settings()


settings: Settings = get_settings()
