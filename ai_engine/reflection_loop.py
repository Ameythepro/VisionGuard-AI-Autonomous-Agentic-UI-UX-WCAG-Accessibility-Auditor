"""
VisionGuard AI - Reflection Loop
===================================
Closed-loop self-verification mechanism for AI-generated CSS patches.

Cycle:
    1. **PROPOSE** — The agent generates a CSS patch for a violation.
    2. **INJECT**  — The SandboxInjector applies it in an isolated browser.
    3. **VERIFY**  — Re-extract computed styles and re-run WCAG checks.
    4. **DECIDE**  — Accept the patch if compliant, otherwise request
                     a revised patch from the agent.

This loop ensures that every CSS fix is mathematically validated
against the WCAG 2.1 contrast formula before it appears in the
final audit report.

Safety: the loop caps at ``MAX_ITERATIONS`` (default 3) to prevent
runaway API calls or infinite retries.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, TYPE_CHECKING

from playwright.async_api import async_playwright

if TYPE_CHECKING:
    # Avoid circular import at module load time.  At runtime
    # the agent is passed in as a plain object and duck-typed.
    from .agent_engine import VisionGuardAgent

# These are pure utility functions — safe to import at module level.
from .agent_engine import (
    parse_rgb,
    relative_luminance,
    contrast_ratio,
    run_wcag_audit,
)

# Sibling-package imports (project root already on sys.path
# thanks to agent_engine.py).
from browser_automation.browser_engine import BrowserEngine
from browser_automation.sandbox_injector import SandboxInjector, SandboxResult

logger = logging.getLogger("visionguard.reflection_loop")


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class ReflectionIteration:
    """Records one pass of the propose → inject → verify cycle."""

    iteration: int
    css_patch: str
    violations_before: int
    violations_after: int
    improvement_pct: float
    resolved: bool
    sandbox_result: Optional[dict] = None
    details: str = ""


@dataclass
class ReflectionResult:
    """Aggregate result of the full reflection loop."""

    total_iterations: int
    final_patch: str
    fully_resolved: bool
    original_violations: int
    remaining_violations: int
    iterations: List[dict] = field(default_factory=list)
    duration_seconds: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Reflection Loop
# ═══════════════════════════════════════════════════════════════


class ReflectionLoop:
    """
    Iterative closed-loop verification for CSS accessibility patches.

    Each iteration:
    1. Injects the CSS patch into an isolated browser via
       :class:`SandboxInjector` and captures before/after screenshots.
    2. Re-extracts computed styles from the patched page.
    3. Re-runs the WCAG contrast checker on the new styles.
    4. If violations remain and iterations are left, asks the
       ``VisionGuardAgent`` for a revised patch.

    Usage::

        loop = ReflectionLoop(browser_engine, sandbox_injector, agent)
        results = await loop.run(url, css_patch, violations)
    """

    MAX_ITERATIONS = 3

    def __init__(
        self,
        browser_engine: BrowserEngine,
        sandbox_injector: SandboxInjector,
        agent: "VisionGuardAgent",
    ):
        self.browser_engine = browser_engine
        self.sandbox_injector = sandbox_injector
        self.agent = agent

    # ─────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────

    async def run(
        self,
        url: str,
        css_patch: str,
        original_violations: List[dict],
        output_dir: str = "temp_screenshots/reflection",
    ) -> List[dict]:
        """
        Execute the reflection loop.

        Args:
            url:                  Target page URL.
            css_patch:            Initial CSS patch to verify.
            original_violations:  Violation dicts from the WCAG audit.
            output_dir:           Directory for reflection screenshots.

        Returns:
            List containing a single :class:`ReflectionResult` dict
            (wrapped in a list for consistency with the report schema).
        """
        start_time = time.time()
        iterations: List[dict] = []
        current_patch = css_patch
        original_count = len(original_violations)

        logger.info(
            "Reflection loop starting | %d violations | max %d iterations",
            original_count,
            self.MAX_ITERATIONS,
        )

        for i in range(1, self.MAX_ITERATIONS + 1):
            logger.info("  Iteration %d/%d …", i, self.MAX_ITERATIONS)

            iteration = await self._run_single_iteration(
                iteration_num=i,
                url=url,
                css_patch=current_patch,
                original_violations=original_violations,
                original_count=original_count,
                output_dir=output_dir,
            )

            iterations.append(asdict(iteration))

            logger.info(
                "  Iteration %d: %d → %d violations (%s)",
                i,
                iteration.violations_before,
                iteration.violations_after,
                "✅ RESOLVED" if iteration.resolved else "⚠️  partial",
            )

            if iteration.resolved:
                logger.info(
                    "  All violations resolved after %d iteration(s)!", i,
                )
                break

            # ── Ask agent for a revised patch ────────────────
            if i < self.MAX_ITERATIONS and getattr(
                self.agent, "_ai_available", False
            ):
                worst = self._pick_worst_violation(original_violations)
                if worst:
                    revised = await self.agent.request_revised_patch(
                        original_violation=worst,
                        css_patch=current_patch,
                        ratio_before=worst.get("contrast_ratio", 1.0),
                        ratio_after=worst.get("contrast_ratio", 1.0),
                        required_ratio=worst.get("required_ratio", 4.5),
                    )
                    if revised:
                        current_patch = current_patch + "\n" + revised
                        logger.info("  Received revised patch from agent")
                    else:
                        logger.info(
                            "  No revised patch available — stopping loop"
                        )
                        break
            else:
                break

        duration = round(time.time() - start_time, 2)

        final = iterations[-1] if iterations else {}

        result = ReflectionResult(
            total_iterations=len(iterations),
            final_patch=current_patch,
            fully_resolved=final.get("resolved", False),
            original_violations=original_count,
            remaining_violations=final.get(
                "violations_after", original_count
            ),
            iterations=iterations,
            duration_seconds=duration,
        )

        logger.info(
            "Reflection loop complete | %d iterations | %.2fs | %s",
            result.total_iterations,
            duration,
            "RESOLVED" if result.fully_resolved else "PARTIAL",
        )

        return [asdict(result)]

    # ─────────────────────────────────────────────────────────
    # Single iteration
    # ─────────────────────────────────────────────────────────

    async def _run_single_iteration(
        self,
        iteration_num: int,
        url: str,
        css_patch: str,
        original_violations: List[dict],
        original_count: int,
        output_dir: str,
    ) -> ReflectionIteration:
        """
        Execute one propose → inject → verify → decide cycle.
        """
        sandbox_data: Optional[dict] = None

        try:
            # ── Step A: Visual diff via SandboxInjector ──────
            iter_dir = os.path.join(
                output_dir, f"iteration_{iteration_num}",
            )
            sandbox_result: SandboxResult = (
                await self.sandbox_injector.apply_and_verify(
                    url=url,
                    css_patch=css_patch,
                    output_dir=iter_dir,
                )
            )
            sandbox_data = {
                "sandbox": True,
                "success": sandbox_result.success,
                "before": sandbox_result.original_screenshot,
                "after": sandbox_result.patched_screenshot,
                "error": sandbox_result.error,
            }

            # ── Step B: Re-extract styles with patch applied ─
            patched_styles = await self._extract_styles_with_patch(
                url, css_patch,
            )

            # ── Step C: Re-run WCAG checks ───────────────────
            new_violations, _ = run_wcag_audit(patched_styles)

            violations_after = len(new_violations)
            improvement = round(
                (1 - violations_after / max(original_count, 1)) * 100, 1,
            )
            resolved = violations_after == 0

            return ReflectionIteration(
                iteration=iteration_num,
                css_patch=css_patch,
                violations_before=original_count,
                violations_after=violations_after,
                improvement_pct=improvement,
                resolved=resolved,
                sandbox_result=sandbox_data,
                details=(
                    f"Reduced from {original_count} to "
                    f"{violations_after} violations "
                    f"({improvement}% improvement)"
                ),
            )

        except Exception as exc:
            logger.error(
                "Reflection iteration %d failed: %s",
                iteration_num, exc,
            )
            return ReflectionIteration(
                iteration=iteration_num,
                css_patch=css_patch,
                violations_before=original_count,
                violations_after=original_count,
                improvement_pct=0.0,
                resolved=False,
                sandbox_result=sandbox_data,
                details=f"Error: {type(exc).__name__}: {exc}",
            )

    # ─────────────────────────────────────────────────────────
    # Patched-page style extraction
    # ─────────────────────────────────────────────────────────

    async def _extract_styles_with_patch(
        self,
        url: str,
        css_patch: str,
    ) -> List[dict]:
        """
        Navigate to the URL, inject the CSS patch, then extract
        computed styles — combining SandboxInjector's injection
        technique with BrowserEngine's style-extraction JS.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(1000)

                # Inject the CSS patch as a <style> element
                safe_css = css_patch.replace("\\", "\\\\").replace(
                    "`", "\\`"
                )
                await page.evaluate(
                    f"""
                    (() => {{
                        const style = document.createElement('style');
                        style.setAttribute(
                            'data-visionguard', 'reflection-patch'
                        );
                        style.textContent = `{safe_css}`;
                        document.head.appendChild(style);
                    }})()
                    """
                )

                # Let the browser re-render
                await page.wait_for_timeout(500)

                # Re-use the exact same extraction JS as BrowserEngine
                styles: List[dict] = await page.evaluate(
                    """
                    () => {
                        const elements = document.querySelectorAll(
                            'p, span, a, h1, h2, h3, h4, h5, h6, li, ' +
                            'td, th, label, button, input, textarea, ' +
                            'select, figcaption, blockquote, cite, code, ' +
                            'pre, strong, em, small, div'
                        );
                        const results = [];

                        for (const el of elements) {
                            const text = el.innerText?.trim();
                            if (!text || text.length === 0) continue;

                            const computed = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();

                            if (rect.width === 0 || rect.height === 0)
                                continue;
                            if (
                                computed.display === 'none' ||
                                computed.visibility === 'hidden'
                            )
                                continue;

                            results.push({
                                tag: el.tagName.toLowerCase(),
                                text: text.substring(0, 200),
                                color: computed.color,
                                backgroundColor: computed.backgroundColor,
                                fontSize: computed.fontSize,
                                fontWeight: computed.fontWeight,
                                boundingBox: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                },
                                selector: el.id
                                    ? '#' + el.id
                                    : el.className
                                        ? el.tagName.toLowerCase() +
                                          '.' +
                                          el.className
                                              .split(' ')
                                              .join('.')
                                        : el.tagName.toLowerCase(),
                            });
                        }
                        return results;
                    }
                    """
                )

                return styles

            finally:
                await context.close()
                await browser.close()

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _pick_worst_violation(violations: List[dict]) -> Optional[dict]:
        """Return the violation with the lowest contrast ratio."""
        if not violations:
            return None
        return min(
            violations,
            key=lambda v: v.get("contrast_ratio", 999),
        )
