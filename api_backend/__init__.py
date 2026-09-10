"""
VisionGuard AI - API Backend Module
=====================================
Async FastAPI gateway with Redis caching for the VisionGuard pipeline.
"""

from .redis_cache import RedisCache

__all__ = ["RedisCache"]
