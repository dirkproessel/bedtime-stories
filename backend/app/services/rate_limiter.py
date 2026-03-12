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
        # Default limits
        self.limits = {
            "tts": 100,
            "text": 10000,
            "image": 70
        }
        
        # Sliding window for requests: service_name -> list of timestamps
        self._request_timestamps = {}
        
        self.usage_file = settings.AUDIO_OUTPUT_DIR / "api_usage_v2.json"
        
        # In-memory daily cache
        self._today = ""
        self._daily_counts = {} # service_name -> count
        self._load_usage()

    def _load_usage(self):
        try:
            if self.usage_file.exists():
                data = json.loads(self.usage_file.read_text(encoding="utf-8"))
                self._today = data.get("date", "")
                self._daily_counts = data.get("counts", {})
        except Exception as e:
            logger.error(f"Failed to load API usage: {e}")

    def _save_usage(self):
        try:
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text(json.dumps({
                "date": self._today,
                "counts": self._daily_counts
            }), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save API usage: {e}")

    def _check_and_reset_daily(self):
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._today != today_str:
            self._today = today_str
            self._daily_counts = {}
            self._save_usage()

    def has_daily_quota(self, service: str = "tts") -> bool:
        """Returns True if we still have daily quota left for the service."""
        self._check_and_reset_daily()
        limit = self.limits.get(service, 100)
        count = self._daily_counts.get(service, 0)
        
        # Leave a tiny buffer
        if count >= (limit - 1):
            logger.warning(f"Rate Limiter: Daily quota for {service} exhausted ({count}/{limit}).")
            return False
        return True

    def increment_daily_quota(self, service: str = "tts"):
        """Records a request against the daily quota for a specific service."""
        self._check_and_reset_daily()
        self._daily_counts[service] = self._daily_counts.get(service, 0) + 1
        self._save_usage()

    async def wait_for_capacity(self, service: str = "tts"):
        """
        Blocks until there is capacity in the RPM window for the specific service.
        Must be called before sending an API request.
        """
        now = time.time()
        
        if service not in self._request_timestamps:
            self._request_timestamps[service] = []
            
        # RPM limits: TTS=10, Text=1000, Image=10
        rpm_limits = {
            "tts": 10,
            "text": 1000,
            "image": 10
        }
        rpm_limit = rpm_limits.get(service, 10)

        # Clean up old timestamps (> 60s ago)
        self._request_timestamps[service] = [t for t in self._request_timestamps[service] if now - t < 60.0]
        
        # If we have reached the limit for the last minute, calculate wait time
        # We use limit - 1 to be slightly conservative
        if len(self._request_timestamps[service]) >= (rpm_limit - 1):
            # We need to wait until the oldest request in our window falls out
            oldest = self._request_timestamps[service][0]
            wait_time = 60.0 - (now - oldest)
            if wait_time > 0:
                logger.info(f"Rate Limiter: RPM limit approaching for {service} ({len(self._request_timestamps[service])} reqs in 60s). Sleeping for {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                
            # Clean up again after sleeping
            now = time.time()
            self._request_timestamps[service] = [t for t in self._request_timestamps[service] if now - t < 60.0]

        # Record this request
        self._request_timestamps[service].append(time.time())

# Singleton instance
rate_limiter = RateLimiter()
