import time
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_request_log: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW   = 60


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory IP-based rate limiter.
    - Repo batch file requests (X-Batch-Request: true) bypass rate limiting.
    - Manual single paste requests are limited to 5/min per IP.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            if request.method == "POST" and request.url.path == "/review-code":

                # Repo batch file analysis — bypass rate limit entirely
                is_batch = request.headers.get("X-Batch-Request", "false").lower() == "true"
                if is_batch:
                    return await call_next(request)

                # Safe IP extraction
                ip = "unknown"
                if request.client and request.client.host:
                    ip = request.client.host

                now = time.time()

                # Clean entries outside the current window
                _request_log[ip] = [
                    t for t in _request_log[ip]
                    if now - t < RATE_LIMIT_WINDOW
                ]

                if len(_request_log[ip]) >= RATE_LIMIT_REQUESTS:
                    logger.warning(f"Rate limit exceeded for IP: {ip}")
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error":  "Rate limit exceeded.",
                            "detail": f"Maximum {RATE_LIMIT_REQUESTS} requests "
                                      f"per {RATE_LIMIT_WINDOW} seconds allowed.",
                            "retry_after_seconds": RATE_LIMIT_WINDOW,
                        }
                    )

                _request_log[ip].append(now)

        except Exception as e:
            # Middleware must NEVER crash the request
            logger.error(f"Rate limiter error (non-fatal): {e}")

        return await call_next(request)