"""One error shape for every failure: {"error": {"code", "message", "fields"}}."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from services.analysis import TripError
from services.http import ProviderError


def error_response(code: str, message: str, http_status: int, fields: dict | None = None) -> Response:
    return Response({"error": {"code": code, "message": message, "fields": fields or {}}}, status=http_status)


def exception_handler(exc, context):
    if isinstance(exc, TripError):
        return error_response("invalid_trip", str(exc), status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, ProviderError):
        return error_response("provider_unavailable", str(exc), status.HTTP_502_BAD_GATEWAY)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(detail, dict):
        return error_response("validation_error", "Please check the highlighted fields.", 400, detail)
    message = detail.get("detail", "Request failed.") if isinstance(detail, dict) else "Request failed."
    return error_response("request_failed", str(message), response.status_code)
