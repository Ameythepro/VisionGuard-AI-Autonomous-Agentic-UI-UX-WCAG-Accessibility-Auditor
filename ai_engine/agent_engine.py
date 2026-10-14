"""
VisionGuard AI - Agent Engine
================================
Core AI orchestrator for the VisionGuard accessibility audit pipeline.

This module:
1. Captures web page screenshots and computed styles via BrowserEngine
2. Runs deterministic WCAG 2.1 contrast checks (built-in math engine)
3. Sends screenshots + violation data to Google Gemini for multimodal analysis
4. Generates CSS patches to fix identified violations
5. Orchestrates the reflection loop for closed-loop verification

Operating Modes:
- **AI-Enhanced Mode**: When a Gemini API key is configured, uses multimodal
  LLM analysis for deeper insight and automated CSS patch generation.
- **Deterministic Mode**: When no API key is available, runs only the
  mathematical WCAG checks and generates rule-based patches.
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("visionguard.agent_engine")

# ─────────────────────────────────────────────────────────────
# Conditional imports — gracefully handle missing packages
# ─────────────────────────────────────────────────────────────
_GENAI_AVAILABLE = False
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    logger.warning(
        "google-generativeai not installed. "
        "AI-enhanced mode disabled; running deterministic-only."
    )

_PIL_AVAILABLE = False
try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore[assignment, misc]
    logger.warning(
        "Pillow not installed. "
        "Multimodal screenshot analysis disabled."
    )

# Ensure project root is importable for sibling-package access
import sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from browser_automation.browser_engine import BrowserEngine, AuditCapture
from browser_automation.sandbox_injector import SandboxInjector, SandboxResult

from .prompt_templates import (
    SYSTEM_UIUX_REVIEWER,
    SYSTEM_ACCESSIBILITY_FIXER,
    HUMAN_AUDIT_TEMPLATE,
    HUMAN_FIX_TEMPLATE,
    REFLECTION_TEMPLATE,
)


# ═══════════════════════════════════════════════════════════════
# SECTION 1: Built-in WCAG 2.1 Contrast Mathematics
# ═══════════════════════════════════════════════════════════════
# Embedded directly so the AI engine is fully self-contained
# and doesn't depend on the dom_accessibility module.
#
# Reference: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
# Reference: https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio


def parse_rgb(css_color: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse a CSS color string into an (R, G, B) tuple.

    Supported formats:
        rgb(128, 128, 128)
        rgba(128, 128, 128, 1)
        rgba(128, 128, 128, 0.5)

    Args:
        css_color: A CSS ``rgb()`` or ``rgba()`` string.

    Returns:
        ``(R, G, B)`` integers in 0-255, or ``None`` if unparseable.
    """
    if not css_color or not isinstance(css_color, str):
        return None

    match = re.match(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d.]+)?\s*\)",
        css_color.strip(),
    )
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    return None


def srgb_to_linear(channel: float) -> float:
    """
    Convert a single sRGB channel value (0.0 – 1.0) to linear light
    per the WCAG 2.1 specification.

    Formula:
        if C ≤ 0.04045  →  C_lin = C / 12.92
        else             →  C_lin = ((C + 0.055) / 1.055) ^ 2.4
    """
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(r: int, g: int, b: int) -> float:
    """
    Calculate WCAG 2.1 relative luminance from 8-bit RGB values.

    L = 0.2126 × R_lin + 0.7152 × G_lin + 0.0722 × B_lin

    Returns:
        Luminance between 0.0 (black) and 1.0 (white).
    """
    r_lin = srgb_to_linear(r / 255.0)
    g_lin = srgb_to_linear(g / 255.0)
    b_lin = srgb_to_linear(b / 255.0)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(l1: float, l2: float) -> float:
    """
    Calculate the WCAG contrast ratio between two relative luminances.

    Formula: (L_lighter + 0.05) / (L_darker + 0.05)

    Returns:
        Ratio ≥ 1.0  (e.g. 21.0 for pure black on white).
    """
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_large_text(font_size: str, font_weight: str) -> bool:
    """
    Determine whether text qualifies as "large text" under WCAG 2.1.

    Large text:
        ≥ 18 pt (24 px) at any weight, **or**
        ≥ 14 pt (≈ 18.66 px) if bold (font-weight ≥ 700).
    """
    try:
        size_match = re.match(r"([\d.]+)", font_size or "16")
        weight_match = re.match(r"(\d+)", font_weight or "400")
        if not size_match or not weight_match:
            return False
        size_px = float(size_match.group(1))
        weight = int(weight_match.group(1))
    except (AttributeError, ValueError):
        return False

    if size_px >= 24.0:
        return True
    if size_px >= 18.66 and weight >= 700:
        return True
    return False


def check_element_contrast(element: dict) -> Optional[dict]:
    """
    Check WCAG 2.1 color-contrast compliance for one DOM element.

    Args:
        element: Dict from ``BrowserEngine.extract_computed_styles()``
                 (keys: color, backgroundColor, fontSize, fontWeight …).

    Returns:
        A violation dict if the element **fails** WCAG AA, else ``None``.
    """
    fg_rgb = parse_rgb(element.get("color", ""))
    bg_rgb = parse_rgb(element.get("backgroundColor", ""))

    if fg_rgb is None or bg_rgb is None:
        return None  # Cannot evaluate — skip silently

    # Skip fully transparent backgrounds  (rgba(…, 0))
    bg_str = element.get("backgroundColor", "")
    alpha_match = re.search(r"rgba\([^)]*,\s*([\d.]+)\s*\)", bg_str)
    if alpha_match and float(alpha_match.group(1)) == 0:
        return None

    fg_lum = relative_luminance(*fg_rgb)
    bg_lum = relative_luminance(*bg_rgb)
    ratio = contrast_ratio(fg_lum, bg_lum)

    large = is_large_text(
        element.get("fontSize", "16px"),
        element.get("fontWeight", "400"),
    )

    aa_threshold = 3.0 if large else 4.5
    aaa_threshold = 4.5 if large else 7.0

    aa_pass = ratio >= aa_threshold
    aaa_pass = ratio >= aaa_threshold

    if aa_pass:
        return None  # Passes AA — no violation

    # Severity heuristic based on how far below threshold
    if ratio < 2.0:
        severity = "critical"
    elif ratio < 3.0:
        severity = "high"
    else:
        severity = "medium"

    return {
        "element_tag": element.get("tag", "unknown"),
        "element_text": element.get("text", "")[:100],
        "selector": element.get("selector", ""),
        "foreground_color": element.get("color", ""),
        "background_color": element.get("backgroundColor", ""),
        "contrast_ratio": round(ratio, 2),
        "required_ratio": aa_threshold,
        "is_large_text": large,
        "font_size": element.get("fontSize", ""),
        "font_weight": element.get("fontWeight", ""),
        "wcag_aa": "FAIL",
        "wcag_aaa": "PASS" if aaa_pass else "FAIL",
        "severity": severity,
        "bounding_box": element.get("boundingBox", {}),
    }


def run_wcag_audit(
    computed_styles: List[dict],
) -> Tuple[List[dict], dict]:
    """
    Run WCAG 2.1 contrast checks on every element from the page.

    Args:
        computed_styles: List returned by
            ``BrowserEngine.extract_computed_styles()``.

    Returns:
        ``(violations, summary)`` — a list of violation dicts and
        a statistics summary dict.
    """
    violations: List[dict] = []
    total_checked = 0
    total_passed = 0

    for element in computed_styles:
        total_checked += 1
        violation = check_element_contrast(element)
        if violation is not None:
            violation["id"] = f"contrast_{len(violations) + 1}"
            violations.append(violation)
        else:
            total_passed += 1

    summary = {
        "total_elements_checked": total_checked,
        "total_passed": total_passed,
        "total_violations": len(violations),
        "aa_pass_rate": round(
            total_passed / max(total_checked, 1) * 100, 1
        ),
        "critical_count": sum(
            1 for v in violations if v["severity"] == "critical"
        ),
        "high_count": sum(
            1 for v in violations if v["severity"] == "high"
        ),
        "medium_count": sum(
            1 for v in violations if v["severity"] == "medium"
        ),
    }

    return violations, summary


# ═══════════════════════════════════════════════════════════════
# SECTION 2: Data Classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class AuditReport:
    """Complete audit report produced by ``VisionGuardAgent.run_audit()``."""

    audit_id: str
    url: str
    timestamp: str
    duration_seconds: float
    mode: str  # "ai_enhanced" or "deterministic"

    # WCAG contrast results
    violations: List[dict] = field(default_factory=list)
    wcag_summary: dict = field(default_factory=dict)

    # AI-enhanced analysis (None in deterministic mode)
    ai_analysis: Optional[dict] = None

    # CSS patches
    patches: List[dict] = field(default_factory=list)
    combined_css_patch: str = ""

    # Reflection loop results
    reflection_results: List[dict] = field(default_factory=list)

    # Screenshots & sandbox
    screenshots: Dict[str, str] = field(default_factory=dict)
    sandbox_results: List[dict] = field(default_factory=list)

    # Page metadata
    page_title: str = ""
    viewports_captured: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialise the report to a plain dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# SECTION 3: VisionGuard AI Agent
# ═══════════════════════════════════════════════════════════════


class VisionGuardAgent:
    """
    Core AI agent that orchestrates the full VisionGuard
    accessibility audit pipeline.

    Dual-mode operation:
    - **AI-Enhanced** — Gemini multimodal analysis + CSS patch generation
    - **Deterministic** — pure WCAG math + rule-based patches (no API key)

    Usage::

        agent = VisionGuardAgent()              # reads GOOGLE_API_KEY from .env
        report = await agent.run_audit("https://example.com")
        print(report["wcag_summary"])
    """

    DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_MODEL,
        headless: bool = True,
    ):
        """
        Initialise the VisionGuard agent.

        Args:
            api_key:     Google Gemini API key.  Falls back to the
                         ``GOOGLE_API_KEY`` environment variable.
            model_name:  Gemini model identifier (default: gemini-3.5-flash-lite).
            headless:    Run the Playwright browser in headless mode.
        """
        self.model_name = model_name
        self.headless = headless
        self._model = None
        self._ai_available = False

        # ── Resolve API key ──────────────────────────────────
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        # ── Initialise Gemini (if possible) ──────────────────
        if self.api_key and _GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
                self._ai_available = True
                logger.info(
                    "Gemini initialised → model: %s", self.model_name
                )
            except Exception as exc:
                logger.error("Failed to initialise Gemini: %s", exc)
                self._ai_available = False
        else:
            if not self.api_key:
                logger.info(
                    "No GOOGLE_API_KEY configured → deterministic mode."
                )
            if not _GENAI_AVAILABLE:
                logger.info(
                    "google-generativeai package not installed → "
                    "deterministic mode."
                )

        # ── Initialise browser tools ─────────────────────────
        self.browser_engine = BrowserEngine(headless=headless)
        self.sandbox_injector = SandboxInjector(headless=headless)

        logger.info(
            "VisionGuardAgent ready | mode=%s",
            "ai_enhanced" if self._ai_available else "deterministic",
        )

    async def _call_gemini_with_fallback(self, contents: any) -> any:
        """Call Gemini model with automatic fallback if primary model gets 503 or 429."""
        models_to_try = [
            self.model_name,
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
            "gemini-3.5-flash",
        ]
        seen = set()
        unique_models = []
        for m in models_to_try:
            if m and m not in seen:
                seen.add(m)
                unique_models.append(m)

        last_exc = None
        contents_list = contents if isinstance(contents, list) else [contents]
        for m_name in unique_models:
            try:
                model = genai.GenerativeModel(m_name)
                response = await asyncio.to_thread(
                    model.generate_content,
                    contents=contents_list,
                    request_options={"retry": None}
                )
                if response and response.text:
                    logger.info("Agent Gemini call succeeded with model: %s", m_name)
                    return response
            except Exception as e:
                last_exc = e
                logger.warning("Agent Gemini model %s failed (%s: %s); trying fallback...", m_name, type(e).__name__, e)
                continue
        raise last_exc or RuntimeError("All Gemini models failed")

    # ─────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        """Current operating mode: ``'ai_enhanced'`` or ``'deterministic'``."""
        return "ai_enhanced" if self._ai_available else "deterministic"

    # ─────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────

    async def run_audit(
        self,
        url: str,
        output_dir: str = "temp_screenshots",
    ) -> dict:
        """
        Run a complete accessibility audit on the given URL.

        Pipeline:
            1. Page capture   → screenshots + computed styles
            2. WCAG checks    → deterministic contrast violations
            3. LLM analysis   → multimodal screenshot review  (AI mode)
            4. Patch gen       → CSS fixes for violations       (AI mode)
            5. Reflection loop → sandbox-verify each patch      (AI mode)

        Args:
            url:        Target URL to audit.
            output_dir: Base directory for screenshot output.

        Returns:
            Complete audit report as a plain dict.
        """
        audit_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        logger.info(
            "[%s] ═══ Starting %s audit for: %s",
            audit_id, self.mode, url,
        )

        report = AuditReport(
            audit_id=audit_id,
            url=url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=0.0,
            mode=self.mode,
        )

        try:
            # ── Step 1: Capture page data ────────────────────
            logger.info("[%s] Step 1/5: Capturing page data…", audit_id)
            audit_capture, computed_styles = await self._capture_page_data(
                url, output_dir, audit_id,
            )

            if audit_capture.captures:
                first_cap = next(iter(audit_capture.captures.values()))
                report.page_title = first_cap.page_title
            report.viewports_captured = list(audit_capture.captures.keys())
            report.screenshots = {
                name: cap.screenshot_path
                for name, cap in audit_capture.captures.items()
            }

            # ── Step 2: Deterministic WCAG contrast checks ───
            logger.info(
                "[%s] Step 2/5: Running WCAG contrast checks…", audit_id,
            )
            violations, wcag_summary = run_wcag_audit(computed_styles)
            report.violations = violations
            report.wcag_summary = wcag_summary

            logger.info(
                "[%s] WCAG: %d violations / %d elements (%.1f%% pass)",
                audit_id,
                wcag_summary["total_violations"],
                wcag_summary["total_elements_checked"],
                wcag_summary["aa_pass_rate"],
            )

            # ── Step 3: AI multimodal analysis (optional) ────
            if self._ai_available and _PIL_AVAILABLE:
                logger.info(
                    "[%s] Step 3/5: AI multimodal analysis…", audit_id,
                )
                screenshot_path = report.screenshots.get(
                    "desktop_1080p",
                    next(iter(report.screenshots.values()), None),
                )
                if screenshot_path and os.path.exists(screenshot_path):
                    ai_analysis = await self._analyze_with_llm(
                        screenshot_path=screenshot_path,
                        violations=violations,
                        computed_styles=computed_styles,
                        url=url,
                        page_title=report.page_title,
                    )
                    report.ai_analysis = ai_analysis
                else:
                    logger.warning(
                        "[%s] No screenshot available for AI analysis",
                        audit_id,
                    )
            else:
                logger.info(
                    "[%s] Step 3/5: Skipped (deterministic mode)", audit_id,
                )

            # ── Step 4: Generate CSS patches ─────────────────
            if violations:
                logger.info(
                    "[%s] Step 4/5: Generating CSS patches…", audit_id,
                )
                if self._ai_available:
                    patches = await self._generate_patches(violations, url)
                else:
                    patches = self._generate_deterministic_patches(violations)

                report.patches = patches.get("patches", [])
                report.combined_css_patch = patches.get("combined_patch", "")
            else:
                logger.info(
                    "[%s] Step 4/5: Skipped (no violations found)", audit_id,
                )

            # ── Step 5: Reflection loop ──────────────────────
            if report.combined_css_patch and violations:
                logger.info(
                    "[%s] Step 5/5: Running reflection loop…", audit_id,
                )
                # Lazy import to avoid circular dependency at module level
                from .reflection_loop import ReflectionLoop

                loop = ReflectionLoop(
                    browser_engine=self.browser_engine,
                    sandbox_injector=self.sandbox_injector,
                    agent=self,
                )
                reflection_results = await loop.run(
                    url=url,
                    css_patch=report.combined_css_patch,
                    original_violations=violations,
                )
                report.reflection_results = reflection_results
            else:
                logger.info(
                    "[%s] Step 5/5: Skipped (no patches to verify)", audit_id,
                )

        except Exception as exc:
            logger.error(
                "[%s] Audit failed: %s", audit_id, exc, exc_info=True,
            )
            report.wcag_summary["error"] = (
                f"{type(exc).__name__}: {exc}"
            )

        report.duration_seconds = round(time.time() - start_time, 2)

        logger.info(
            "[%s] ═══ Audit complete | %.2fs | %s | "
            "violations=%d | patches=%d",
            audit_id,
            report.duration_seconds,
            report.mode,
            len(report.violations),
            len(report.patches),
        )

        return report.to_dict()

    # ─────────────────────────────────────────────────────────
    # Internal pipeline stages
    # ─────────────────────────────────────────────────────────

    async def _capture_page_data(
        self,
        url: str,
        output_dir: str,
        audit_id: str,
    ) -> Tuple[AuditCapture, List[dict]]:
        """
        Use the ``BrowserEngine`` to capture screenshots across
        viewports and extract computed CSS styles.
        """
        capture_dir = os.path.join(output_dir, f"audit_{audit_id}")

        audit_capture = await self.browser_engine.capture_page(
            url, capture_dir,
        )
        computed_styles = await self.browser_engine.extract_computed_styles(url)

        logger.info(
            "Captured %d viewports, extracted %d styled elements",
            len(audit_capture.captures),
            len(computed_styles),
        )
        return audit_capture, computed_styles

    async def _analyze_with_llm(
        self,
        screenshot_path: str,
        violations: List[dict],
        computed_styles: List[dict],
        url: str,
        page_title: str,
    ) -> Optional[dict]:
        """
        Send the desktop screenshot + violations data to Gemini
        for multimodal accessibility analysis.
        """
        if not self._model or not _PIL_AVAILABLE:
            return None

        try:
            image = Image.open(screenshot_path)

            # Truncate for token budget
            violations_json = json.dumps(violations[:20], indent=2)

            # Summarise element counts by tag
            tag_counts: Dict[str, int] = {}
            for style in computed_styles:
                tag = style.get("tag", "unknown")
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            styles_summary = json.dumps(tag_counts, indent=2)

            human_msg = HUMAN_AUDIT_TEMPLATE.format(
                url=url,
                page_title=page_title,
                viewport="desktop_1080p (1920×1080)",
                violation_count=len(violations),
                violations_json=violations_json,
                styles_count=len(computed_styles),
                styles_summary=styles_summary,
            )

            full_prompt = SYSTEM_UIUX_REVIEWER + "\n\n" + human_msg

            # Call Gemini with automatic fallback to lite models
            response = await self._call_gemini_with_fallback([full_prompt, image])

            return self._parse_llm_json(response.text)

        except Exception as exc:
            logger.error("LLM analysis failed: %s", exc, exc_info=True)
            return {"error": str(exc)}

    async def _generate_patches(
        self,
        violations: List[dict],
        url: str,
    ) -> dict:
        """
        Ask Gemini to produce CSS patches for the detected violations.
        Falls back to deterministic patches if the LLM call fails.
        """
        if not self._model:
            return self._generate_deterministic_patches(violations)

        try:
            violations_json = json.dumps(violations[:15], indent=2)

            human_msg = HUMAN_FIX_TEMPLATE.format(
                url=url,
                violations_json=violations_json,
            )

            full_prompt = SYSTEM_ACCESSIBILITY_FIXER + "\n\n" + human_msg

            response = await self._call_gemini_with_fallback(full_prompt)

            result = self._parse_llm_json(response.text)

            if result and "patches" in result:
                return result

            logger.warning(
                "LLM did not return patches in expected format; "
                "falling back to deterministic."
            )
            return self._generate_deterministic_patches(violations)

        except Exception as exc:
            logger.error(
                "LLM patch generation failed: %s → deterministic fallback",
                exc,
            )
            return self._generate_deterministic_patches(violations)

    # ─────────────────────────────────────────────────────────
    # Deterministic patch generation (no LLM required)
    # ─────────────────────────────────────────────────────────

    def _generate_deterministic_patches(
        self,
        violations: List[dict],
    ) -> dict:
        """
        Generate CSS patches using pure math — no LLM required.

        Strategy: for each contrast violation, compute whether the
        background is light or dark and pick a foreground color
        that exceeds the WCAG AA threshold.
        """
        patches: List[dict] = []
        css_rules: List[str] = []

        for violation in violations:
            selector = violation.get("selector", "")
            if not selector:
                continue

            required = violation.get("required_ratio", 4.5)
            bg_rgb = parse_rgb(violation.get("background_color", ""))

            if bg_rgb is None:
                continue

            bg_lum = relative_luminance(*bg_rgb)

            # Choose a text color that will meet the threshold
            if bg_lum > 0.1791:
                # Light background → use dark text
                # Find how dark we need to go
                # (bg_lum + 0.05) / (fg_lum + 0.05) >= required
                # fg_lum <= (bg_lum + 0.05) / required - 0.05
                target_lum = (bg_lum + 0.05) / required - 0.05
                target_lum = max(target_lum, 0.0)
                # Map to a gray value (approximate)
                fix_color = self._luminance_to_hex(target_lum)
            else:
                # Dark background → use light text
                # (fg_lum + 0.05) / (bg_lum + 0.05) >= required
                # fg_lum >= required * (bg_lum + 0.05) - 0.05
                target_lum = required * (bg_lum + 0.05) - 0.05
                target_lum = min(target_lum, 1.0)
                fix_color = self._luminance_to_hex(target_lum)

            css_rule = f"{selector} {{ color: {fix_color}; }}"
            patches.append({
                "violation_id": violation.get("id", ""),
                "selector": selector,
                "css_properties": {"color": fix_color},
                "css_rule": css_rule,
                "rationale": (
                    f"Adjusted text color to {fix_color} to achieve "
                    f"≥ {required}:1 contrast against "
                    f"{violation.get('background_color', 'unknown')} background"
                ),
            })
            css_rules.append(css_rule)

        return {
            "patches": patches,
            "combined_patch": "\n".join(css_rules),
        }

    @staticmethod
    def _luminance_to_hex(target_luminance: float) -> str:
        """
        Convert a target relative luminance to an approximate hex
        gray colour.  Uses a binary search on the sRGB gamma curve
        to find the 8-bit gray value.
        """
        target_luminance = max(0.0, min(1.0, target_luminance))

        low, high = 0, 255
        while low < high:
            mid = (low + high) // 2
            lum = relative_luminance(mid, mid, mid)
            if lum < target_luminance:
                low = mid + 1
            else:
                high = mid

        gray = max(0, min(255, low))
        return f"#{gray:02x}{gray:02x}{gray:02x}"

    # ─────────────────────────────────────────────────────────
    # LLM helpers
    # ─────────────────────────────────────────────────────────

    def _parse_llm_json(self, text: str) -> Optional[dict]:
        """
        Robustly parse a JSON object from an LLM response.

        Tries, in order:
        1. Direct ``json.loads``
        2. Extract from markdown ```json ... ``` fence
        3. Extract first ``{ … }`` block via regex
        """
        if not text:
            return None

        cleaned = text.strip()

        # Attempt 1: direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt 2: markdown code fence
        fence_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL,
        )
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Attempt 3: first { … } block
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(
            "Failed to parse LLM JSON — raw response: %.200s…", cleaned,
        )
        return {"raw_response": text}

    async def request_revised_patch(
        self,
        original_violation: dict,
        css_patch: str,
        ratio_before: float,
        ratio_after: float,
        required_ratio: float,
    ) -> Optional[str]:
        """
        Ask the LLM for a revised CSS patch when the previous one
        did not fully resolve the violation.

        Used internally by the :class:`ReflectionLoop`.

        Returns:
            New CSS rule string, or ``None`` if unavailable.
        """
        if not self._model:
            return None

        try:
            status = (
                "PASS — violation resolved"
                if ratio_after >= required_ratio
                else "STILL FAILING — needs stronger fix"
            )

            prompt = REFLECTION_TEMPLATE.format(
                original_violation=json.dumps(
                    original_violation, indent=2,
                ),
                css_patch=css_patch,
                ratio_before=round(ratio_before, 2),
                ratio_after=round(ratio_after, 2),
                required_ratio=required_ratio,
                status=status,
            )

            full_prompt = SYSTEM_ACCESSIBILITY_FIXER + "\n\n" + prompt

            response = await self._call_gemini_with_fallback(full_prompt)

            result = self._parse_llm_json(response.text)

            if result and result.get("revised_patch"):
                return result["revised_patch"]
            return None

        except Exception as exc:
            logger.error("Revised-patch request failed: %s", exc)
            return None
