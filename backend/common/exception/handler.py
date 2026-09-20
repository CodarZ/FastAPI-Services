import json

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.utils import is_body_allowed_for_status_code
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, PlainTextResponse, Response

from backend.common.exception.errors import BaseAppException
from backend.common.log import log
from backend.common.request.trace_id import gen_trace_id, parse_trace_id
from backend.common.response.base import ErrorDetail, ResponseModel, response_base
from backend.core.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request

__all__ = [
    'register_exception_handlers',
    'standard_error_responses',
]

# 500 错误的默认脱敏提示文案
_MASKED_500_MESSAGE = 'Internal server error.'


def _status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return 'Request failed.'


def _resolve_trace(request: Request) -> tuple[str, bool]:
    """解析请求的 TraceID，不存在时生成并标记."""
    state = request.scope.get('state')
    state_trace = state.get('trace_id') if isinstance(state, dict) else None
    if state_trace:
        return state_trace, False

    raw = request.headers.get(settings.TRACE_ID_HEADER)
    if raw:
        parsed = parse_trace_id(request.headers)
        if parsed == raw.strip().lower():
            return parsed, False
    return gen_trace_id(), True


def _merged_headers(extra: dict[str, str] | None, trace_id: str) -> dict[str, str]:
    """合并自定义响应头与 TraceID 响应头."""
    headers = {key: str(value) for key, value in extra.items()} if extra else {}
    headers[settings.TRACE_ID_HEADER] = trace_id
    return headers


def _masked_message(status_code: int, message: str) -> str:
    """处理服务端异常文案.

    非 development 环境脱敏不展示详细错误信息.
    """
    if status_code >= 500 and settings.ENVIRONMENT != 'development':
        return _MASKED_500_MESSAGE
    return message


def _cors_fallback_headers(request: Request) -> dict[str, str]:
    """兜底层 CORS 最小合成.

    复刻 CORSMiddleware simple_response 的 send 谓词
    """
    if not settings.MIDDLEWARE_CORS:
        return {}
    origin = request.headers.get('origin')
    if not origin:
        return {}

    allow_all = '*' in settings.CORS_ALLOWED_ORIGINS
    headers: dict[str, str] = {}
    if allow_all and settings.CORS_ALLOW_CREDENTIALS:
        # 浏览器禁止 ACAO '*' 与 credentials 并存, 中间件的同款处理是回显具体 origin
        headers['Access-Control-Allow-Origin'] = origin
        headers['Vary'] = 'Origin'
    elif allow_all:
        headers['Access-Control-Allow-Origin'] = '*'
    elif origin in settings.CORS_ALLOWED_ORIGINS:
        headers['Access-Control-Allow-Origin'] = origin
        headers['Vary'] = 'Origin'

    if headers.get('Access-Control-Allow-Origin') and settings.CORS_ALLOW_CREDENTIALS:
        headers['Access-Control-Allow-Credentials'] = 'true'
    return headers


def _error_response(
    *,
    status_code: int,
    message: str,
    trace_id: str,
    error_details: list[ErrorDetail] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Response:
    """统一构造错误响应，序列化失败时自动降级."""
    headers = _merged_headers(extra_headers, trace_id)
    try:
        body = response_base.fail(message=message, code=status_code, errors=error_details, trace_id=trace_id)
        content = jsonable_encoder(body.model_dump())
        return JSONResponse(status_code=status_code, content=content, headers=headers)
    except Exception:  # ruff: ignore[blind-except] -- 构造失败降级处理
        fallback = {
            'code': status_code,
            'message': message,
            'data': None,
            'trace_id': trace_id,
            'errors': None,
        }
        return JSONResponse(status_code=status_code, content=fallback, headers=headers)


def _handle_app_exception(request: Request, exc: BaseAppException) -> Response:
    trace_id, generated = _resolve_trace(request)
    error_details = exc.errors
    if error_details is None:
        error_details = [ErrorDetail(code=exc.error_code)]

    bound = log.bind(
        path=request.url.path,
        method=request.method,
        status=exc.status_code,
        error_code=exc.error_code,
    )
    if generated:
        bound = bound.bind(generated_trace_id=True)
    if exc.status_code >= 500:
        bound.opt(exception=exc).error('{} - 业务服务异常: {}', request.url.path, exc.message)
    else:
        bound.warning('{} - 业务异常: {}', request.url.path, exc.message)

    return _error_response(
        status_code=exc.status_code,
        message=_masked_message(exc.status_code, exc.message),
        trace_id=trace_id,
        error_details=error_details,
        extra_headers=exc.headers,
    )


def _handle_http_exception(request: Request, exc: HTTPException) -> Response:
    trace_id, _ = _resolve_trace(request)
    status_code = exc.status_code

    if status_code >= 500:
        log.bind(path=request.url.path, method=request.method, status=status_code).opt(exception=exc).error(
            '{} - 服务异常: {}', request.url.path, _status_phrase(status_code)
        )
    elif status_code in (401, 403):
        log.bind(path=request.url.path, method=request.method, status=status_code).warning(
            '{} - 安全异常: {}', request.url.path, _status_phrase(status_code)
        )
    elif status_code in (404, 405):
        log.bind(path=request.url.path, method=request.method, status=status_code).warning(
            '{} - 路由异常: {}', request.url.path, _status_phrase(status_code)
        )
    else:
        log.bind(path=request.url.path, method=request.method, status=status_code).warning(
            '{} - 请求异常: {}', request.url.path, _status_phrase(status_code)
        )

    if not is_body_allowed_for_status_code(status_code):
        return Response(status_code=status_code, headers=_merged_headers(exc.headers, trace_id))

    error_details: list[ErrorDetail] | None = None
    if isinstance(exc.detail, str):
        message = exc.detail or _status_phrase(status_code)
    elif exc.detail is not None:
        encoded = jsonable_encoder(exc.detail)
        text = encoded if isinstance(encoded, str) else json.dumps(encoded, ensure_ascii=False, default=str)
        error_details = [ErrorDetail(message=text)]
        message = _status_phrase(status_code)
    else:
        message = _status_phrase(status_code)

    return _error_response(
        status_code=status_code,
        message=_masked_message(status_code, message),
        trace_id=trace_id,
        error_details=error_details,
        extra_headers=exc.headers,
    )


def _escape_pointer_token(token: str) -> str:
    """转义 JSON Pointer 字符."""
    return token.replace('~', '~0').replace('/', '~1')


def _loc_to_pointer(loc: tuple[Any, ...] | list[Any]) -> str:
    return '/' + '/'.join(_escape_pointer_token(str(part)) for part in loc)


def _clean_validation_message(msg: Any) -> str | None:
    """清理校验错误信息中的默认前缀."""
    if not isinstance(msg, str):
        return None
    for prefix in ('Value error, ', 'Assertion failed, '):
        if msg.startswith(prefix):
            return msg[len(prefix) :]
    return msg


def _handle_validation_error(request: Request, exc: RequestValidationError) -> Response:
    """处理请求参数校验异常 (422)."""
    trace_id, _ = _resolve_trace(request)
    keep_message = settings.ENVIRONMENT == 'development'

    error_details: list[ErrorDetail] = []
    log_items: list[dict[str, Any]] = []
    for item in exc.errors():
        loc = item.get('loc') or ()
        field = _loc_to_pointer(loc) if loc else None
        cleaned = _clean_validation_message(item.get('msg'))
        error_details.append(ErrorDetail(field=field, type=item.get('type'), message=cleaned if keep_message else None))
        log_items.append({'loc': list(loc), 'type': item.get('type'), 'msg': cleaned if keep_message else None})

    log.bind(
        path=request.url.path,
        method=request.method,
        status=422,
        error_code='REQUEST_VALIDATION_FAILED',
        validation_errors=log_items,
    ).warning('{} - 请求校验失败(422): {}', request.url.path, len(error_details))

    return _error_response(
        status_code=422,
        message='Request validation failed.',
        trace_id=trace_id,
        error_details=error_details,
    )


def _handle_unhandled_exception(request: Request, exc: Exception) -> Response:
    """处理全局未捕获异常 (500 兜底)."""
    trace_id, generated = _resolve_trace(request)

    bound = log.bind(request_id=trace_id, path=request.url.path, method=request.method, status=500)
    if generated:
        bound = bound.bind(generated_trace_id=True)
    bound.opt(exception=exc).error('{} - 未接管异常: {}', request.url.path, type(exc).__name__)

    message = (str(exc) or type(exc).__name__) if settings.ENVIRONMENT == 'development' else _MASKED_500_MESSAGE
    content = {'code': 500, 'message': message, 'data': None, 'trace_id': trace_id, 'errors': None}
    headers = _merged_headers(None, trace_id) | _cors_fallback_headers(request)
    try:
        return JSONResponse(status_code=500, content=content, headers=headers)
    except Exception:  # ruff: ignore[blind-except] -- 兜底响应失败返回纯文本
        return PlainTextResponse(_MASKED_500_MESSAGE, status_code=500, headers=headers)


def _iter_subclasses(cls: type[BaseAppException]) -> list[type[BaseAppException]]:
    found: list[type[BaseAppException]] = []

    def walk(current: type[BaseAppException]) -> None:
        for sub in current.__subclasses__():
            found.append(sub)
            walk(sub)

    walk(cls)
    return found


def standard_error_responses(*codes: int) -> dict[int, dict[str, Any]]:
    """生成 OpenAPI 错误响应模型配置.

    用法: @router.post('/x', responses=standard_error_responses(404, 429))
    """
    by_status: dict[int, type[BaseAppException]] = {}
    for sub in _iter_subclasses(BaseAppException):
        by_status.setdefault(sub.status_code, sub)

    responses: dict[int, dict[str, Any]] = {}
    for code in codes:
        if code == 422:
            message = 'Request validation failed.'
            errors: list[dict[str, Any]] | None = [
                {'field': '/body/name', 'code': None, 'message': None, 'type': 'string_pattern_mismatch'}
            ]
        else:
            exc_cls = by_status.get(code)
            message = exc_cls.message if exc_cls else _status_phrase(code)
            errors = None
        responses[code] = {
            'description': f'{_status_phrase(code)} (HTTP {code})',
            'content': {
                'application/json': {
                    'example': {
                        'code': code,
                        'message': message,
                        'data': None,
                        'trace_id': None,
                        'errors': errors,
                    }
                }
            },
        }
    return responses


def _patch_openapi(app: FastAPI) -> None:
    """统一 OpenAPI 中的 422 验证错误响应模型定义."""
    original_openapi = app.openapi

    def openapi_with_error_contract() -> dict[str, Any]:
        schema = original_openapi()
        components = schema.setdefault('components', {}).setdefault('schemas', {})

        envelope = ResponseModel[None].model_json_schema(ref_template='#/components/schemas/{model}')
        definitions: dict[str, Any] = envelope.pop('$defs', {})
        envelope['title'] = 'HTTPValidationError'
        components['HTTPValidationError'] = envelope
        if 'ErrorDetail' in definitions:
            components['ErrorDetail'] = definitions['ErrorDetail']

        production_example = {
            'code': 422,
            'message': 'Request validation failed.',
            'data': None,
            'trace_id': None,
            'errors': [{'field': '/body/name', 'code': None, 'message': None, 'type': 'string_pattern_mismatch'}],
        }
        for operations in schema.get('paths', {}).values():
            for operation in operations.values():
                declared = operation.get('responses', {}).get('422')
                if not declared:
                    continue
                for media in declared.get('content', {}).values():
                    ref = media.get('schema', {}).get('$ref', '')
                    if ref.endswith('/HTTPValidationError'):
                        media['example'] = production_example
        return schema

    app.openapi = openapi_with_error_contract


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器."""
    app.add_exception_handler(BaseAppException, _handle_app_exception)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unhandled_exception)
    _patch_openapi(app)
