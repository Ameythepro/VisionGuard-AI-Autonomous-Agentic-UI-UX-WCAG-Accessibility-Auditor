"""
VisionGuard AI - AI Engine Module
===================================
Agentic AI orchestrator for autonomous WCAG 2.1 accessibility auditing.

Provides:

* :class:`VisionGuardAgent` — The core AI agent that drives the full
  audit pipeline (capture → WCAG check → LLM analysis → patch → verify).
* :class:`ReflectionLoop` — Closed-loop sandbox verification for CSS patches.
* Built-in WCAG 2.1 contrast mathematics (no external dependencies).
* Expert-crafted prompt templates for Google Gemini multimodal analysis.

Quick start::

    from ai_engine import VisionGuardAgent

    agent = VisionGuardAgent()   # reads GOOGLE_API_KEY from .env
    report = await agent.run_audit("https://example.com")
"""

from .agent_engine import (
    # Core agent
    VisionGuardAgent,
    AuditReport,
    # WCAG math utilities
    parse_rgb,
    srgb_to_linear,
    relative_luminance,
    contrast_ratio,
    is_large_text,
    check_element_contrast,
    run_wcag_audit,
)

from .reflection_loop import (
    ReflectionLoop,
    ReflectionResult,
    ReflectionIteration,
)

from .prompt_templates import (
    SYSTEM_UIUX_REVIEWER,
    SYSTEM_ACCESSIBILITY_FIXER,
    HUMAN_AUDIT_TEMPLATE,
    HUMAN_FIX_TEMPLATE,
    REFLECTION_TEMPLATE,
)

__all__ = [
    # Core agent
    "VisionGuardAgent",
    "AuditReport",
    # Reflection loop
    "ReflectionLoop",
    "ReflectionResult",
    "ReflectionIteration",
    # WCAG utilities
    "parse_rgb",
    "srgb_to_linear",
    "relative_luminance",
    "contrast_ratio",
    "is_large_text",
    "check_element_contrast",
    "run_wcag_audit",
    # Prompt templates
    "SYSTEM_UIUX_REVIEWER",
    "SYSTEM_ACCESSIBILITY_FIXER",
    "HUMAN_AUDIT_TEMPLATE",
    "HUMAN_FIX_TEMPLATE",
    "REFLECTION_TEMPLATE",
]
