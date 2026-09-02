"""P0.5 统一错误处理 —— FastAPI 异常 handler，输出统一 JSON 错误结构。

统一错误响应体：
{
  "error": {"code": "ERR_CODE", "message": "人读信息", "detail": {...}}
}
- HTTPException（含 401/403/400/404...）→ code 用 UNPROCESSABLE/自定义，message 用 detail
- RequestValidationError → code VALIDATION_ERROR，detail 给字段级错误
- 未捕获 Exception → code INTERNAL_ERROR，message 通用，避免泄露内部细节（生产）
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("yika.errors")


def error_response(code: str, message: str, status: int, detail=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "detail": detail or {}}
    })


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # 状态码 → 统一 code 映射（可扩展）
        code_map = {
            400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
            404: "NOT_FOUND", 409: "CONFLICT", 423: "LOCKED",
            422: "UNPROCESSABLE", 500: "INTERNAL_ERROR",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        return error_response(code, str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return error_response("VALIDATION_ERROR", "请求参数校验失败", 422, detail=exc.errors())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("未捕获异常: %s %s", request.method, request.url.path)
        # 生产不泄露内部错误细节
        return error_response("INTERNAL_ERROR", "服务器内部错误", 500)
