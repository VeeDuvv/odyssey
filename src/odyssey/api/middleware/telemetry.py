"""Request telemetry middleware — logs every request for the future introspector."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from odyssey.storage.postgres import postgres_store


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Logs request telemetry to PostgreSQL for introspector consumption."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = int((time.monotonic() - start) * 1000)

        # Log async — don't block the response
        try:
            await postgres_store.execute(
                """
                INSERT INTO telemetry (event_type, query, latency_ms, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                "api_request",
                f"{request.method} {request.url.path}",
                latency_ms,
                f'{{"status": {response.status_code}}}',
            )
        except Exception:
            pass  # Telemetry should never break the request

        return response
