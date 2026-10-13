"""
VisionGuard AI - Sandbox Injector
==================================
Injects CSS patches into a live browser page inside an isolated sandbox
context, then re-captures the page to verify that the patch resolves
the identified accessibility or layout issue.

This is the "closed-loop verification" mechanism: the AI agent proposes
a CSS fix, this module applies it in a sandboxed browser, and the system
compares "before" vs "after" screenshots to confirm the fix.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import async_playwright, Page

from .viewport_manager import ViewportManager, ViewportConfig

logger = logging.getLogger("visionguard.sandbox_injector")


@dataclass
class SandboxResult:
    """Result of a sandboxed CSS patch injection and re-capture."""
    original_screenshot: str
    patched_screenshot: str
    css_patch: str
    viewport_name: str
    success: bool
    error: Optional[str] = None
    timestamp: float = 0.0


class SandboxInjector:
    """
    Applies CSS patches to a live page in an isolated browser context
    and captures before/after screenshots for visual diff comparison.
    
    Workflow:
    1. Load the target URL in a clean browser context.
    2. Capture the "before" screenshot.
    3. Inject the proposed CSS patch via <style> tag.
    4. Capture the "after" screenshot.
    5. Return both screenshots for the AI reflection loop to compare.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def apply_and_verify(
        self,
        url: str,
        css_patch: str,
        output_dir: str = "temp_screenshots/sandbox",
        viewport_name: str = "desktop_1080p",
    ) -> SandboxResult:
        """
        Applies a CSS patch to the target page and captures before/after.
        
        Args:
            url: Target page URL.
            css_patch: Raw CSS string to inject (e.g., "body { color: #333; }").
            output_dir: Directory to save the before/after screenshots.
            viewport_name: Which viewport preset to use for the test.
        
        Returns:
            SandboxResult with paths to both screenshots.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        vp_config = ViewportManager.get_viewport(viewport_name)
        if vp_config is None:
            vp_config = list(ViewportManager.get_default_audit_viewports().values())[0]
        
        context_opts = ViewportManager.to_playwright_context_options(vp_config)
        timestamp = int(time.time())
        
        before_path = os.path.join(output_dir, f"before_{viewport_name}_{timestamp}.png")
        after_path = os.path.join(output_dir, f"after_{viewport_name}_{timestamp}.png")

        logger.info(f"Sandbox: applying CSS patch to {url} at {viewport_name}")
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            
            try:
                # ---- BEFORE: Capture the original page ----
                ctx_before = await browser.new_context(**context_opts)
                page_before = await ctx_before.new_page()
                await page_before.goto(url, wait_until="domcontentloaded")
                await page_before.wait_for_timeout(1000)
                await page_before.screenshot(path=before_path, full_page=True)
                await ctx_before.close()
                
                # ---- AFTER: Capture the page with CSS patch injected ----
                ctx_after = await browser.new_context(**context_opts)
                page_after = await ctx_after.new_page()
                await page_after.goto(url, wait_until="domcontentloaded")
                await page_after.wait_for_timeout(500)
                
                # Inject the CSS patch as a <style> tag at the end of <head>
                await self._inject_css(page_after, css_patch)
                
                # Wait for the browser to re-render with the patch applied
                await page_after.wait_for_timeout(500)
                await page_after.screenshot(path=after_path, full_page=True)
                await ctx_after.close()
                
                logger.info(f"Sandbox: before/after captured successfully")
                
                return SandboxResult(
                    original_screenshot=before_path.replace("\\", "/").lstrip("/"),
                    patched_screenshot=after_path.replace("\\", "/").lstrip("/"),
                    css_patch=css_patch,
                    viewport_name=viewport_name,
                    success=True,
                    timestamp=time.time(),
                )
                
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.error(f"Sandbox injection failed: {error_msg}")
                return SandboxResult(
                    original_screenshot=before_path.replace("\\", "/").lstrip("/"),
                    patched_screenshot=after_path.replace("\\", "/").lstrip("/"),
                    css_patch=css_patch,
                    viewport_name=viewport_name,
                    success=False,
                    error=error_msg,
                    timestamp=time.time(),
                )
            finally:
                await browser.close()

    async def _inject_css(self, page: Page, css_patch: str) -> None:
        """
        Injects a CSS patch into the page by adding a <style> element.
        The style is tagged with a data attribute for easy identification.
        """
        # Escape backticks and backslashes for safe JS template literal injection
        safe_css = css_patch.replace("\\", "\\\\").replace("`", "\\`")
        
        await page.evaluate(f"""
            (() => {{
                const style = document.createElement('style');
                style.setAttribute('data-visionguard', 'css-patch');
                style.textContent = `{safe_css}`;
                document.head.appendChild(style);
            }})()
        """)
        logger.debug(f"Injected CSS patch ({len(css_patch)} chars)")

    async def apply_multiple_patches(
        self,
        url: str,
        patches: list,
        output_dir: str = "temp_screenshots/sandbox",
        viewport_name: str = "desktop_1080p",
    ) -> list:
        """
        Applies multiple CSS patches sequentially and returns results for each.
        Useful when the AI agent suggests multiple fixes.
        
        Args:
            url: Target URL.
            patches: List of CSS patch strings.
            output_dir: Screenshot output directory.
            viewport_name: Viewport to test against.
        
        Returns:
            List of SandboxResult objects, one per patch.
        """
        results = []
        for i, patch in enumerate(patches):
            patch_dir = os.path.join(output_dir, f"patch_{i}")
            result = await self.apply_and_verify(url, patch, patch_dir, viewport_name)
            results.append(result)
            logger.info(f"Patch {i}: {'✅ success' if result.success else '❌ failed'}")
        return results
