"""
VisionGuard AI - DOM Accessibility Module
============================================
Provides HTML/CSS parsing, deterministic WCAG 2.1 mathematical
compliance checking, and CSS AST extraction/validation.

This is the "Symbolic Engine" of the Neuro-Symbolic architecture.
All calculations here are deterministic — no AI, no LLM, no guessing.
"""

from .dom_parser import DOMParser, DOMViolation, DOMAnalysisResult
from .wcag_checker import (
    WCAGLevel,
    Severity,
    ContrastResult,
    ContrastViolation,
    AccessibilityAuditResult,
    parse_color,
    linearize_srgb_channel,
    relative_luminance,
    contrast_ratio,
    check_contrast,
    audit_computed_styles,
    simulate_color_blindness,
    check_contrast_for_color_blind,
    suggest_fix_color,
)
from .ast_extractor import (
    ASTExtractor,
    CSSRule,
    CSSValidationResult,
    UnifiedDiagnostic,
)

__all__ = [
    # DOM Parser
    "DOMParser",
    "DOMViolation",
    "DOMAnalysisResult",
    # WCAG Checker
    "WCAGLevel",
    "Severity",
    "ContrastResult",
    "ContrastViolation",
    "AccessibilityAuditResult",
    "parse_color",
    "linearize_srgb_channel",
    "relative_luminance",
    "contrast_ratio",
    "check_contrast",
    "audit_computed_styles",
    "simulate_color_blindness",
    "check_contrast_for_color_blind",
    "suggest_fix_color",
    # AST Extractor
    "ASTExtractor",
    "CSSRule",
    "CSSValidationResult",
    "UnifiedDiagnostic",
]
