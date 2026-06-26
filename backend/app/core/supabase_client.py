import time
import logging

import httpx
from supabase import create_client, Client
from postgrest._sync.request_builder import SyncQueryRequestBuilder

from app.core.config import settings

logger = logging.getLogger(__name__)

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

# ---------------------------------------------------------------------------
# Resilience patch: retry on transient transport errors (e.g. "Server
# disconnected" / RemoteProtocolError from HTTP/2 connections to Supabase),
# which are not retried by postgrest's built-in send_with_retry (that only
# retries on 503/520 HTTP responses, not on connection-level exceptions).
# Without this, a single dropped connection turns into a 500 on dashboard /
# analytics / evidence endpoints even though the data itself is fine.
# ---------------------------------------------------------------------------
_RETRYABLE_EXCEPTIONS = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.ReadTimeout,
    httpx.WriteError,
    httpx.PoolTimeout,
)

_original_execute = SyncQueryRequestBuilder.execute


def _execute_with_retry(self, *args, **kwargs):
    last_exc = None
    for attempt in range(3):
        try:
            return _original_execute(self, *args, **kwargs)
        except _RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc
            logger.warning(
                "Supabase request failed with transient error (attempt %d/3): %s",
                attempt + 1, exc,
            )
            time.sleep(0.5 * (attempt + 1))
    raise last_exc


SyncQueryRequestBuilder.execute = _execute_with_retry
