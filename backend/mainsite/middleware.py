import logging
import time

logger = logging.getLogger("mainsite.access")

# Probes and metric scrapes hit these every few seconds per pod.
QUIET_PATHS = {"/healthz/", "/metrics"}


class AccessLogMiddleware:
    """Log one line per request, with its fields also passed as `extra` for the JSON formatter."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # A failing probe or scrape is exactly what to keep.
        if request.path in QUIET_PATHS and response.status_code < 400:
            return response

        path = request.get_full_path()
        logger.info(
            "%s %s %d %.1fms",
            request.method,
            path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
        return response
