"""
API Rate Limiter Service.
Handles RPM (Requests Per Minute) sliding window and RPD (Requests Per Day) tracking.
"""

import time
import asyncio
import json
import logging
from datetime import datetime, timezone
from app.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        # We set RPM to 10 based on Gemini 2.5 Flash Free Tier
        self.rpm_limit = 10
        # We set RPD to 100 based on Gemini 2.5 Flash Free Tier
        self.rpd_limit = 100
        
        # Sliding window for requests: timestamps of recent requests
        self._request_timestamps = []
        
        self.usage_file = settings.AUDIO_OUTPUT_DIR / "api_usage.json"
        
        # In-memory daily cache
        self._today = ""
        self._daily_count = 0
        self._load_usage()

    def _load_usage(self):
        try:
            if self.usage_file.exists():
                data = json.loads(self.usage_file.read_text(encoding="utf-8"))
                self._today = data.get("date", "")
                self._daily_count = data.get("count", 0)
        except Exception as e:
            logger.error(f"Failed to load API usage: {e}")

    def _save_usage(self):
        try:
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text(json.dumps({
                "date": self._today,
                "count": self._daily_count
            }), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save API usage: {e}")

    def _check_and_reset_daily(self):
        # Note: Depending on the API, quotas might reset at midnight UTC or another timezone.
        # We use UTC here as a safe default.
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._today != today_str:
            self._today = today_str
            self._daily_count = 0
            self._save_usage()

    def has_daily_quota(self) -> bool:
        """Returns True if we still have daily quota left, False otherwise."""
        self._check_and_reset_daily()
        # Leave a tiny buffer of 2 requests just in case
        if self._daily_count >= (self.rpd_limit - 2):
            logger.warning(f"Rate Limiter: Daily quota exhausted ({self._daily_count}/{self.rpd_limit}).")
            return False
        return True

    def increment_daily_quota(self):
        """Records a request against the daily quota."""
        self._check_and_reset_daily()
        self._daily_count += 1
        self._save_usage()

    async def wait_for_capacity(self):
        """
        Blocks until there is capacity in the RPM window.
        Must be called before sending an API request.
        """
        now = time.time()
        
        # Clean up old timestamps (> 60s ago)
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]
        
        # If we have reached the limit for the last minute, calculate wait time
        # We use rpm_limit - 1 to be slightly conservative
        if len(self._request_timestamps) >= (self.rpm_limit - 1):
            # We need to wait until the oldest request in our window falls out
            oldest = self._request_timestamps[0]
            wait_time = 60.0 - (now - oldest)
            if wait_time > 0:
                logger.info(f"Rate Limiter: RPM limit approaching ({len(self._request_timestamps)} reqs in 60s). Sleeping for {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                
            # Clean up again after sleeping
            now = time.time()
            self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]

        # Record this request
        self._request_timestamps.append(time.time())

# Singleton instance
rate_limiter = RateLimiter()
