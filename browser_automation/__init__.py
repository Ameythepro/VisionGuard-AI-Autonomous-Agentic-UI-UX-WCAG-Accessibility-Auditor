"""
VisionGuard AI - Browser Automation Module
===========================================
Provides headless browser automation for multi-viewport screenshot
capture, DOM extraction, and CSS sandbox injection.
"""

from .viewport_manager import ViewportManager, ViewportConfig
from .browser_engine import BrowserEngine, PageCapture, AuditCapture
from .sandbox_injector import SandboxInjector, SandboxResult

__all__ = [
    "ViewportManager",
    "ViewportConfig",
    "BrowserEngine",
    "PageCapture",
    "AuditCapture",
    "SandboxInjector",
    "SandboxResult",
]
