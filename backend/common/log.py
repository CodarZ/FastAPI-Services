import inspect
import logging
import sys
import traceback

from collections.abc import Mapping, Sequence, Set as AbstractSet
from dataclasses import asdict, is_dataclass
from datetime import UTC
from typing import TYPE_CHECKING, Any

import msgspec

from loguru import logger
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.path import LOG_DIR

if TYPE_CHECKING:
    from loguru import Record

    from backend.common.request.context import _ContextProxy

__all__ = [
    'InterceptHandler',
    'close_logging',
    'log',
    'logger',
    'mask_sensitive_data',
    'setup_logging',
]

log = logger

# 延迟绑定的请求上下文代理单例，避免与 request 模块产生循环导入
_cached_ctx: _ContextProxy | None = None


def _get_request_ctx() -> _ContextProxy:
    """延迟获取请求上下文单例，解除模块循环依赖."""
    global _cached_ctx
    if _cached_ctx is None:
        from backend.common.request.context import ctx

        _cached_ctx = ctx
    return _cached_ctx


# 系统内部专用的 extra 字段名集合
_SYSTEM_EXTRA_KEYS: frozenset[str] = frozenset({
    'caller_display',
    'request_id',
    'tenant_display',
    'tenant_id',
    'thread_display',
    'user_uid',
})

# 预编译默认敏感键名集合
_DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset(k.lower() for k in settings.REQUEST_LOG_ENCRYPT_FIELDS)

# 缓存 both 模式下的最低日志级别数字，避免每条日志重复查询字典
_cached_console_level_no: int = 20
_cached_json_level_no: int = 20


def _mask_sensitive_data_inner(
    data: Any,
    mask: str,
    sensitive_keys: frozenset[str],
    memo: set[int],
    depth: int,
    max_depth: int,
) -> Any:
    """内部递归脱敏."""
    # 基础类型无嵌套关系，直接返回
    if data is None or isinstance(data, (int, float, bool, str, bytes)):
        return data

    # 递归超出最大深度则返回占位符
    if depth >= max_depth:
        return '<MAX_DEPTH_EXCEEDED>'

    # 循环引用保护截断，防止死循环
    obj_id = id(data)
    if obj_id in memo:
        return '<CIRCULAR_REFERENCE>'
    memo.add(obj_id)

    try:
        # 处理 Pydantic v2 模型实例
        if isinstance(data, BaseModel):
            return _mask_sensitive_data_inner(
                data.model_dump(mode='python'),
                mask=mask,
                sensitive_keys=sensitive_keys,
                memo=memo,
                depth=depth + 1,
                max_depth=max_depth,
            )

        # 处理 dataclass 实例 (排除类型本身)
        if is_dataclass(data) and not isinstance(data, type):
            return _mask_sensitive_data_inner(
                asdict(data),
                mask=mask,
                sensitive_keys=sensitive_keys,
                memo=memo,
                depth=depth + 1,
                max_depth=max_depth,
            )

        # 处理字典与映射类型
        if isinstance(data, Mapping):
            result_dict: dict[str, Any] = {}
            for key, val in data.items():
                str_key = str(key).lower()
                # 键命中敏感词则掩码
                if str_key in sensitive_keys:
                    result_dict[key] = mask
                else:
                    # 未命中继续递归
                    result_dict[key] = _mask_sensitive_data_inner(
                        val,
                        mask=mask,
                        sensitive_keys=sensitive_keys,
                        memo=memo,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
            return result_dict

        # 处理列表/元组等序列类型 (排除 str 与 bytes)
        if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
            mapped_items = (
                _mask_sensitive_data_inner(
                    item,
                    mask=mask,
                    sensitive_keys=sensitive_keys,
                    memo=memo,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                for item in data
            )
            return tuple(mapped_items) if isinstance(data, tuple) else list(mapped_items)

        # 处理 set 与 frozenset 集合类型
        if isinstance(data, AbstractSet):
            masked_items = (
                _mask_sensitive_data_inner(
                    item,
                    mask=mask,
                    sensitive_keys=sensitive_keys,
                    memo=memo,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                for item in data
            )
            return frozenset(masked_items) if isinstance(data, frozenset) else set(masked_items)

        return data
    finally:
        memo.remove(obj_id)


def mask_sensitive_data[T](
    data: T,
    mask: str = '******',
    *,
    sensitive_keys: AbstractSet[str] | None = None,
    max_depth: int = 10,
) -> T:
    """深度递归脱敏纯函数.

    Args:
        data: 待脱敏的任意 Python 数据结构 (字典、列表、元组、集合、Pydantic模型、dataclass、标量)。
        mask: 掩码占位符，默认 '******'。
        sensitive_keys: 敏感键名集合 (默认取 _DEFAULT_SENSITIVE_KEYS 常量集合)。
        max_depth: 最大允许递归深度。

    Returns:
        脱敏后的数据副本。
    """
    if sensitive_keys is None:
        keys_to_match = _DEFAULT_SENSITIVE_KEYS
    elif isinstance(sensitive_keys, frozenset):
        keys_to_match = sensitive_keys
    else:
        keys_to_match = frozenset(k.lower() for k in sensitive_keys)

    return _mask_sensitive_data_inner(
        data,
        mask=mask,
        sensitive_keys=keys_to_match,
        memo=set(),
        depth=0,
        max_depth=max_depth,
    )


def _patch_record_context(record: Record) -> None:
    """内部私有 Patcher: 自动注入全链路 TraceID、租户、用户，并对 extra 数据精准脱敏."""
    current_ctx = _cached_ctx if _cached_ctx is not None else _get_request_ctx()

    # 提取底层 RequestContext
    raw_ctx = current_ctx.raw
    extra = record['extra']

    if raw_ctx is not None:
        extra.setdefault('request_id', raw_ctx.trace_id)
        if settings.TENANT_ENABLED:
            tenant = raw_ctx.tenant.tenant_id if raw_ctx.tenant else '-'
            extra.setdefault('tenant_id', tenant)
            extra.setdefault('tenant_display', f'[{tenant}]')
        else:
            extra.setdefault('tenant_id', '-')
            extra.setdefault('tenant_display', '')
        extra.setdefault('user_uid', raw_ctx.user.uid if raw_ctx.user else '-')
    else:
        # 脱离请求上下文的占位
        extra.setdefault('request_id', settings.TRACE_ID_LOG_DEFAULT)
        extra.setdefault('tenant_id', '-')
        extra.setdefault('tenant_display', '[-]' if settings.TENANT_ENABLED else '')
        extra.setdefault('user_uid', '-')

    # 代码位置 (模块名:函数名:代码行号)
    caller = f'{record["name"]}:{record["function"]}:{record["line"]}'
    extra.setdefault('caller_display', caller)

    # 进程与线程标识 (pid:thread_name)
    proc_id = record['process'].id
    th_name = record['thread'].name
    extra.setdefault('thread_display', f'{proc_id}:{th_name}')

    # 优先拦截顶层敏感键，再对复合容器及业务对象深入递归脱敏
    for k, v in list(extra.items()):
        if k in _SYSTEM_EXTRA_KEYS:
            continue

        # 顶层键名命中敏感词
        if str(k).lower() in _DEFAULT_SENSITIVE_KEYS:
            extra[k] = '******'
        # 递归脱敏
        elif (
            isinstance(v, (Mapping, BaseModel))
            or (is_dataclass(v) and not isinstance(v, type))
            or (isinstance(v, (Sequence, AbstractSet)) and not isinstance(v, (str, bytes)))
        ):
            extra[k] = mask_sensitive_data(v, sensitive_keys=_DEFAULT_SENSITIVE_KEYS)


class InterceptHandler(logging.Handler):
    """标准库日志拦截器 (接管 Uvicorn / FastAPI / SQLAlchemy 日志)."""

    def emit(self, record: logging.LogRecord) -> None:
        # 尝试将标准库的日志级别映射到 Loguru，未知级别则回退为原始整数级别
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 动态回溯调用栈帧深度
        # frame: 当前调用栈帧; depth: 跳过 logging 内部帧后的层级深度
        frame, depth = inspect.currentframe(), 0
        # 跳过标准库 logging 内部文件，确保日志记录的代码行号指向业务发起地而非拦截器自身
        while frame and (
            depth == 0 or frame.f_code.co_filename == logging.__file__
        ):  # 继续向上回溯，直到离开 stdlib logging
            frame = frame.f_back  # 进入上一层调用栈帧
            depth += 1

        # Uvicorn 访问日志会因代理传递了非整型状态码导致 %d 格式化崩溃，亦或字典命名占位符缺少键导致 KeyError
        try:
            msg = record.getMessage()
        except TypeError, ValueError, IndexError, KeyError:
            msg = f'{record.msg} [args={record.args!r}]' if record.args else str(record.msg)

        # 修正后的调用栈深度和异常信息，重新投递给 Loguru，确保日志来源和堆栈正确
        logger.opt(depth=depth, exception=record.exc_info).log(level, msg)


# 配置安全编码器
_json_encoder = msgspec.json.Encoder(enc_hook=str)


def _extract_exception_info(exc: Any) -> dict[str, Any]:
    """结构化提取异常信息."""
    exc_type = exc.type
    exc_val = exc.value
    exc_tb = exc.traceback

    type_name = exc_type.__name__ if exc_type else 'Exception'
    module_name = getattr(exc_type, '__module__', '')
    full_type = f'{module_name}.{type_name}' if module_name and module_name != 'builtins' else type_name

    tb_frames = traceback.extract_tb(exc_tb) if exc_tb else []
    last_frame = tb_frames[-1] if tb_frames else None

    # 完整格式化堆栈字符串 (无多行乱行，由 JSON 字段自身容纳换行)
    formatted_stack = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb)).strip()

    info: dict[str, Any] = {
        'code_snippet': last_frame.line if last_frame else '',
        'function': last_frame.name if last_frame else '',
        'location': f'{last_frame.filename}:{last_frame.lineno}' if last_frame else '',
        'message': str(exc_val) if exc_val else '',
        'stacktrace': formatted_stack,
        'type': full_type,
    }

    # 提取业务异常自带的错误码与状态码 (error_code: 显式细码 → 类级 → 推导规范码保底)
    if hasattr(exc_val, 'error_code'):
        info['error_code'] = exc_val.error_code
    if hasattr(exc_val, 'status_code'):
        info['status_code'] = exc_val.status_code

    return info


def _msgspec_json_sink(message: Any) -> None:
    """云原生生产级单行扁平 JSONLines Sink."""
    record = message.record
    extra = record['extra']

    caller = extra.get('caller_display') or f'{record["name"]}:{record["function"]}:{record["line"]}'

    # 构造符合 OpenTelemetry 规范的扁平化 JSON 字典结构，便于 ES / Loki 直接索引检索
    log_entry: dict[str, Any] = {
        'caller': caller,
        'level': record['level'].name,
        'message': record['message'],
        'process': record['process'].id,
        'thread': record['thread'].name,
        'timestamp': record['time'].astimezone(UTC).isoformat(),
        'trace_id': extra.get('request_id', '-'),
        'user_uid': extra.get('user_uid', '-'),
    }

    # 多租户输出 tenant_id
    if settings.TENANT_ENABLED:
        log_entry['tenant_id'] = extra.get('tenant_id', '-')

    # 提取并保留业务自定义 extra 绑定字段
    custom_extra = {k: v for k, v in extra.items() if k not in _SYSTEM_EXTRA_KEYS}
    if custom_extra:
        log_entry['extra'] = custom_extra

    # 结构化全景异常信息
    if record['exception']:
        log_entry['exception'] = _extract_exception_info(record['exception'])

    # 直接向底层缓冲区写入字节流提升吞吐；若无 buffer 属性 (如 StringIO 重定向) 则降级至文本写入
    encoded_bytes = _json_encoder.encode(log_entry) + b'\n'
    buffer = getattr(sys.stdout, 'buffer', None)
    if buffer is not None:
        buffer.write(encoded_bytes)
        buffer.flush()
    else:
        sys.stdout.write(encoded_bytes.decode('utf-8'))
        sys.stdout.flush()


def _both_stdout_sink(message: Any) -> None:
    """控制台彩色文本与生产单行 JSON 联合输出 Sink."""
    record = message.record
    rec_level_no = record['level'].no

    # 控制台彩色文本输出
    if rec_level_no >= _cached_console_level_no:
        sys.stdout.write(str(message))
        sys.stdout.flush()

    # 生产单行 JSON 输出
    if rec_level_no >= _cached_json_level_no:
        _msgspec_json_sink(message)


def setup_logging() -> None:
    """初始化全局结构化日志中枢 (Lifespan 启动阶段调用)."""
    global _cached_console_level_no, _cached_json_level_no

    # 绑定请求上下文代理单例
    _get_request_ctx()

    logger.remove()

    # 刷新配置级别缓存
    _cached_console_level_no = logger.level(settings.LOG_CONSOLE_LEVEL).no
    _cached_json_level_no = logger.level(settings.LOG_JSON_LEVEL).no

    # 动态探测标准输出是否连接至交互式终端 (TTY)，非 TTY 自动禁用 ANSI 颜色标签
    is_tty = sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False

    # 挂载全局
    logger.configure(patcher=_patch_record_context)

    # 动态适配租户模式
    format_console = settings.LOG_FORMAT_CONSOLE
    format_file = settings.LOG_FORMAT_FILE
    if not settings.TENANT_ENABLED:
        format_console = format_console.replace('<blue>{extra[tenant_display]: <16}</> | ', '')
        format_file = format_file.replace('{extra[tenant_display]: <16} | ', '')

    # 纯文本模式
    if settings.LOG_OUTPUT_MODE == 'text':
        logger.add(
            sys.stdout,
            level=settings.LOG_CONSOLE_LEVEL,
            format=format_console,
            colorize=is_tty,
            enqueue=True,  # 推入内部安全队列，异步非阻塞输出
            backtrace=True,  # 异常时记录跨越多层调用栈的完整回溯
            diagnose=False,  # 安全红线：严禁在堆栈中反解打印局部变量，防止密码/Token泄露
        )

    # 云原生 JSON 模式
    elif settings.LOG_OUTPUT_MODE == 'json':
        logger.add(
            _msgspec_json_sink,
            level=settings.LOG_JSON_LEVEL,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

    # 联合模式
    elif settings.LOG_OUTPUT_MODE == 'both':
        min_level_no = min(_cached_console_level_no, _cached_json_level_no)
        logger.add(
            _both_stdout_sink,
            level=min_level_no,
            format=format_console,
            colorize=is_tty,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

    # 物理磁盘文件 Sink 挂载 (纯文本格式)
    if settings.LOG_FILE_ENABLED:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # 全量访问日志：记录 LOG_FILE_LEVEL 及以上级别业务与访问流水
        access_log_path = LOG_DIR / settings.LOG_ACCESS_FILENAME
        logger.add(
            str(access_log_path),
            level=settings.LOG_FILE_LEVEL,
            format=format_file,
            rotation=settings.LOG_ROTATION,  # 每日零点自动切分新文件
            retention=settings.LOG_RETENTION,  # 历史日志自动保留周期 (如 30 days)
            compression='zip',  # 切分后的历史日志自动压缩以节约存储
            encoding='utf-8',
            enqueue=True,  # 专用后台线程异步落盘，彻底杜绝磁盘 I/O 抖动阻塞主事件循环
            backtrace=True,
            diagnose=False,
        )

        # 错误隔离日志：单独仅记录 ERROR 与 CRITICAL 级别日志
        error_log_path = LOG_DIR / settings.LOG_ERROR_FILENAME
        logger.add(
            str(error_log_path),
            level='ERROR',
            format=format_file,
            rotation=settings.LOG_ROTATION,
            retention=settings.LOG_RETENTION,
            compression='zip',
            encoding='utf-8',
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

    # 接管 Python 标准库 logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in (
        'fastapi',
        'sqlalchemy.engine',
        'uvicorn',
        'uvicorn.error',
    ):
        std_logger = logging.getLogger(name)
        # 清除第三方库自带的输出处理器并关闭向上传播，避免同一条日志在控制台出现两次
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    uvicorn_access = logging.getLogger('uvicorn.access')
    uvicorn_access.handlers = [logging.NullHandler()]
    uvicorn_access.propagate = False


async def close_logging() -> None:
    """异步排空并关闭所有日志队列与底层文件句柄 (Lifespan 关闭阶段调用)."""
    await logger.complete()
    logger.remove()
