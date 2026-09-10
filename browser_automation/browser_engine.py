"""
VisionGuard AI - Browser Engine
================================
Asynchronous Playwright-based headless browser engine.
Captures multi-viewport screenshots, extracts full DOM/HTML source,
and collects computed CSS styles from live web pages.

This is the primary data-acquisition layer of the VisionGuard pipeline.
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .viewport_manager import ViewportManager, ViewportConfig

# Module-level logger
logger = logging.getLogger("visionguard.browser_engine")


@dataclass
class PageCapture:
    """
    Holds all data captured from a single viewport render of a page.
    This is the atomic unit of data that flows through the pipeline.
    """
    viewport_name: str
    viewport_width: int
    viewport_height: int
    screenshot_path: str
    html_source: str
    page_title: str
    page_url: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuditCapture:
    """
    Aggregates PageCapture results across all viewports for a single URL audit.
    """
    url: str
    output_dir: str
    captures: Dict[str, PageCapture] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    duration_seconds: float = 0.0


class BrowserEngine:
    """
    Headless browser automation engine using Playwright.
    
    Responsibilities:
    - Launch a headless Chromium instance
    - Navigate to target URLs with configurable wait strategies
    - Capture full-page screenshots at multiple viewport sizes
    - Extract the full HTML source (DOM) of the rendered page
    - Provide per-viewport PageCapture objects for downstream processing
    """
    
    # Maximum time in ms to wait for a page to load
    DEFAULT_NAVIGATION_TIMEOUT = 30_000
    # Time in ms to wait after network idle for JS animations
    POST_LOAD_SETTLE_TIME = 1500

    def __init__(self, headless: bool = True, timeout: int = DEFAULT_NAVIGATION_TIMEOUT):
        self.headless = headless
        self.timeout = timeout

    async def capture_page(
        self,
        url: str,
        output_dir: str = "temp_screenshots",
        viewports: Optional[Dict[str, ViewportConfig]] = None,
    ) -> AuditCapture:
        """
        Main entry point. Navigates to the URL and captures screenshots +
        DOM source across all specified viewports.
        
        Args:
            url: The target URL to audit.
            output_dir: Directory where screenshots will be saved.
            viewports: Optional dict of viewport configs. Defaults to the
                       standard 3-breakpoint audit set.
        
        Returns:
            An AuditCapture object containing all per-viewport results.
        """
        if viewports is None:
            viewports = ViewportManager.get_default_audit_viewports()
        
        os.makedirs(output_dir, exist_ok=True)
        audit = AuditCapture(url=url, output_dir=output_dir)
        start_time = time.time()

        logger.info(f"Starting audit capture for: {url}")
        logger.info(f"Viewports: {list(viewports.keys())}")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            
            try:
                for vp_name, vp_config in viewports.items():
                    try:
                        capture = await self._capture_single_viewport(
                            browser, url, vp_name, vp_config, output_dir
                        )
                        audit.captures[vp_name] = capture
                        logger.info(f"  ✅ {vp_name} ({vp_config.width}x{vp_config.height}) captured")
                    except Exception as e:
                        error_msg = f"{type(e).__name__}: {e}"
                        audit.errors[vp_name] = error_msg
                        logger.error(f"  ❌ {vp_name} failed: {error_msg}")
            finally:
                await browser.close()

        audit.duration_seconds = round(time.time() - start_time, 2)
        logger.info(
            f"Audit capture complete. "
            f"{len(audit.captures)} succeeded, {len(audit.errors)} failed "
            f"in {audit.duration_seconds}s"
        )
        return audit

    async def _capture_single_viewport(
        self,
        browser: Browser,
        url: str,
        viewport_name: str,
        viewport_config: ViewportConfig,
        output_dir: str,
    ) -> PageCapture:
        """
        Captures a single viewport: navigates, waits, screenshots, extracts DOM.
        Each viewport gets its own isolated BrowserContext for clean state.
        """
        context_options = ViewportManager.to_playwright_context_options(viewport_config)
        context: BrowserContext = await browser.new_context(**context_options)
        page: Page = await context.new_page()
        
        try:
            # Set navigation timeout
            page.set_default_navigation_timeout(self.timeout)
            
            # Navigate and wait for network to go idle
            await page.goto(url, wait_until="networkidle")
            
            # Allow JS animations / lazy-loaded content to settle
            await page.wait_for_timeout(self.POST_LOAD_SETTLE_TIME)
            
            # --- Screenshot ---
            filename = f"{viewport_name}_{viewport_config.width}x{viewport_config.height}.png"
            filepath = os.path.join(output_dir, filename)
            await page.screenshot(path=filepath, full_page=True)
            
            # --- Extract rendered HTML (full DOM after JS execution) ---
            html_source = await page.content()
            
            # --- Page metadata ---
            page_title = await page.title()

            return PageCapture(
                viewport_name=viewport_name,
                viewport_width=viewport_config.width,
                viewport_height=viewport_config.height,
                screenshot_path=filepath,
                html_source=html_source,
                page_title=page_title,
                page_url=url,
            )
        finally:
            await context.close()

    async def extract_computed_styles(self, url: str) -> List[dict]:
        """
        Navigates to a URL on a desktop viewport and extracts the computed
        CSS styles of all visible text elements. This data is used by the
        WCAG checker to compute color contrast ratios.
        
        Returns:
            List of dicts, each containing element tag, text, color, 
            background-color, font-size, and bounding box info.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(self.POST_LOAD_SETTLE_TIME)
                
                # JavaScript to extract computed styles of text-bearing elements
                styles = await page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll(
                            'p, span, a, h1, h2, h3, h4, h5, h6, li, td, th, ' +
                            'label, button, input, textarea, select, figcaption, ' +
                            'blockquote, cite, code, pre, strong, em, small, div'
                        );
                        const results = [];
                        
                        for (const el of elements) {
                            const text = el.innerText?.trim();
                            if (!text || text.length === 0) continue;
                            
                            const computed = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            
                            // Skip elements that are not visible
                            if (rect.width === 0 || rect.height === 0) continue;
                            if (computed.display === 'none' || computed.visibility === 'hidden') continue;
                            
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
                                    height: Math.round(rect.height)
                                },
                                selector: el.id 
                                    ? '#' + el.id 
                                    : el.className 
                                        ? el.tagName.toLowerCase() + '.' + el.className.split(' ').join('.')
                                        : el.tagName.toLowerCase()
                            });
                        }
                        return results;
                    }
                """)
                
                logger.info(f"Extracted computed styles for {len(styles)} text elements from {url}")
                return styles
                
            finally:
                await context.close()
                await browser.close()

    async def get_page_html(self, url: str) -> str:
        """
        Simple utility to fetch the fully-rendered HTML of a page.
        Useful for DOM parsing without needing screenshots.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(1000)
                html = await page.content()
                return html
            finally:
                await browser.close()
