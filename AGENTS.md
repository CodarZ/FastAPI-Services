# AGENTS.md

> FastAPI-Services 仓库核心架构准则、协作范式与本地验证规范。

---

## 1. 仓库定位与核心边界 (Scope & Identity)

- **定位**：基于 **Python 3.14+** 与 **FastAPI 0.141+** 的通用企业级异步后端底座模板。
- **包含**：多租户 Schema 隔离、统一身份鉴权（JWT + Redis）、强类型会话工厂、纯异步分页、统一响应契约与全局异常接管、可靠异步任务与本地事务 Outbox。
- **排除**：特定垂直行业业务逻辑（如商城订单、物流配送）。垂直业务需基于本底座扩展或另建业务仓承载。

---

## 2. 技能与分层参考指针 (Context Pointers & Skills)

按需查阅对应技能，避免全量载入上下文：

- **FastAPI** (`.agents/skills/fastapi/SKILL.md`): 路由组织、依赖注入 (`Annotated[..., Depends(...)]`)、SSE/流式响应、生命周期管理器。
- **Pydantic** (`.agents/skills/pydantic/SKILL.md`): DTO 模型、字段约束 (`Annotated[..., Field(...)]`)、自定义校验器与序列化配置。

---

## 3. 核心架构不变式 (Core Invariants)

编写或重构任何代码必须保证满足以下 6 条架构不变式：

1. **类型完备与 PEP 695 原生语法 (Type-First & PEP 695)**：
   - 函数参数与返回值必须携带完整类型标注；泛型统一使用 Python 3.14 PEP 695 原生语法（如 `class ResponseModel[T]` / `def func[T](...)`）。
   - ORM 映射必须使用 SQLAlchemy 2.0+ `Mapped[T]` 与 `mapped_column` 声明。
2. **双 ID 隔离体系 (Dual-ID Architecture)**：
   - 实体主键采用内部自增物理主键 `id: Mapped[id_key]`（`BigInteger`，仅用于数据库索引与物理 JOIN）与对外业务短标识 `uid: Mapped[uid_key]`（Base62 有序短标识，由 `backend.utils.uid:gen_uid` 生成）。
   - 外部 API 接口与 DTO 仅暴露和传递 `uid`，物理 `id` 绝对禁止对外暴露。
3. **绝对时区感知 (Strict UTC Timezone)**：
   - 所有时间操作与数据库时间列必须携带时区信息，当前时间统一使用 `datetime.now(UTC)`。
4. **统一响应包装与纯净契约 (Response Contract Purity)**：
   - 路由出参统一经由 DTO 转换为 `ResponseModel[T]`（通过 `response_base.success(...)` 或 `ResponseModel(...)` 生成），绝对禁止直接返回裸 ORM 实例。
   - 响应信封顶层 `code` 恒等于 HTTP 状态码；错误生命周期内 `data` 恒为 `None`，机器细码及校验明细集中于 `errors: list[ErrorDetail]`。
5. **引用完整性保护 (Restrict On Delete)**：
   - 物理外键关系声明必须显式指定 `ondelete="RESTRICT"`，保护关联审计与核心历史。
6. **凭证驱动租户路由 (Claims-Based Routing)**：
   - 多租户 Schema 隔离（`tenant_{uid}`）必须严格基于经签名验签的 JWT Claims 解析，通过 `get_tenant_db` 与 SQLAlchemy Schema Translate Map 动态路由。

---

## 4. 标准编码范式 (Standard Code Patterns)

### 4.1 ORM 模型定义 (SQLAlchemy 2.0 Async - 基于项目通用底座)

> 社区尚无公认权威的 SQLAlchemy 异步官方 skill；本仓以 `backend/common/model/` 为单一真实源。业务模型统一继承 `Base` 与标准 Mixin：

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model.base import Base
from backend.common.model.mixins import DateTimeMixin
from backend.common.model.types import id_key, uid_key


class User(Base, DateTimeMixin):
    """系统用户."""

    __tablename__ = 'sys_user'

    id: Mapped[id_key]
    uid: Mapped[uid_key]
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment='用户登录名')
    password: Mapped[str] = mapped_column(String(255), comment='Argon2 密码哈希')
```

### 4.2 路由与依赖注入 (对齐 FastAPI Skill)

```python
from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.common.response.base import ResponseModel, response_base
from backend.database.session import get_tenant_db
from backend.modules.user.schemas import UserCreate, UserDetail
from backend.modules.user.services import UserService

router = APIRouter(prefix='/users', tags=['用户管理'])


@router.post('', response_model=ResponseModel[UserDetail], status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreate,
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> ResponseModel[UserDetail]:
    result = await UserService.create_user(db, req)
    return response_base.success(data=result, message='用户创建成功', code=status.HTTP_201_CREATED)
```

### 4.3 结构化业务异常与反探测防护 (Anti-Enumeration)

```python
from backend.common.exception.errors import NotFoundException

# 抛出结构化业务异常，由全局异常处理器接管并统一封装进 ResponseModel 信封
# message: 面向调用方的说明信息；error_code: 写入 errors[].code 的机器可识别细码
# 防枚举：存在但无权访问的敏感资源返回 404 (NOT_FOUND) 语义，避免通过 403 确认资源存在性
if not user:
    raise NotFoundException(message='指定用户不存在', error_code='USER_NOT_FOUND')
```

---

## 5. 工具链与验证工作流 (Toolchain & Verification)

代码交付前必须在本地完整执行以下命令并通过门禁：

```bash
# 1. 代码格式化与静态排版快速修复
uv run ruff check --fix
uv run ruff format

# 2. 预提交质量门禁检查
uv run prek run --all-files

# 3. 自动化测试套件执行 (禁止跳过任何失败项)
uv run pytest

# 4. 数据库迁移 (涉及数据模型变更时必跑)
uv run alembic revision --autogenerate -m "feat: <说明>"
uv run alembic upgrade head
```

### Git 提交规范 (基于 prek & Commitizen `cz`)

项目通过 `.cz.toml` 与 pre-commit 钩子严格校验提交信息：

- **提交方式**：执行 `uv run cz commit` 交互式提交，或遵循 `<type>(<scope>): <subject>` 格式。
- **允许的 17 种 type**：
  - 功能演进：`feat` (新功能), `fix` (修复), `hotfix` (紧急修复), `perf` (性能优化), `refactor` (重构), `revert` (回滚)
  - 质量工程：`style` (代码格式), `test` (测试), `security` (安全修复), `build` (构建脚本), `ci` (工作流), `deps` (依赖变更)
  - 辅助状态：`docs` (文档), `release` (发布), `init` (初始化), `wip` (开发中草稿), `chore` (日常事务)
- **常用 scope**：`app`, `core`, `common`, `database`, `middleware`, `utils`, `main`；子模块使用 `/` 分隔（如 `common/exception`, `core/config`）。

---

## 6. AI Agent 执行行动准则 (Execution Protocol)

1. **先读后写 (Read Before Write)**：修改任何模块前，先阅读对应的基类 (`base.py`)、字段系统 (`types.py`) 或核心契约定义，禁止脱离已有类型定义凭空推导。
2. **手术刀式变更 (Surgical Changes)**：修改范围严格闭环于当前任务目标，严禁重构无关代码；随手清理改动引起的废弃 import 与变量。
3. **闭环验证 (Loop Until Verified)**：交付前必须本地通过 `prek` 与 `pytest`；分析报错根本原因并针对性修复，严禁使用 `# noqa` 或 `# type: ignore` 掩盖问题。
