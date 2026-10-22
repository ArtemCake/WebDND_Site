# backend/app/Services/Core/rate_limit_service.py

"""Простой in-memory rate limiter по IP для публичных auth-эндпоинтов.
"""
from Config.imports import (defaultdict, deque, datetime, timedelta, Lock)


_attempts: dict[str, deque[datetime]] = defaultdict(deque)
_lock = Lock()

async def check_ip_rate_limit(ip: str, limit: int, window_minutes: int) -> bool:
	"""True — лимит превышен, запрос нужно отклонить."""
	now = datetime.utcnow()
	window_start = now - timedelta(minutes=window_minutes)

	async with _lock:
		bucket = _attempts[ip]
		while bucket and bucket[0] < window_start:
			bucket.popleft()

		if len(bucket) >= limit:
			return True

		bucket.append(now)
		return False