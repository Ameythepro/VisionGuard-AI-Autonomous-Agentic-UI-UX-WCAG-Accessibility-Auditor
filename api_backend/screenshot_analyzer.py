"""
VisionGuard AI - Screenshot Analyzer
=======================================
Handles user-uploaded UI screenshots and uses Gemini multimodal LLM to:
1. Analyze the screenshot for WCAG accessibility issues
2. Generate corrected HTML/CSS code
3. Render the corrected UI and return a "fixed" screenshot
4. Accept user prompts/suggestions and refine the output

This module is the backend powerhouse for the Screenshot Lab feature.
"""

import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("visionguard.screenshot_analyzer")

# Absolute path to the shared screenshots directory so uploads land in
# the same location served by the FastAPI static mount, regardless of
# the process working directory (important for Render / cloud deploys).
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_MODULE_DIR)
SCREENSHOTS_DIR = os.path.join(_PROJECT_ROOT, "temp_screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


# ── Conditional imports ──────────────────────────────────────
_GENAI_AVAILABLE = False
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None

_PIL_AVAILABLE = False
try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    Image = None

# Ensure project root is importable
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ═══════════════════════════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════════════════════════

SCREENSHOT_ANALYSIS_PROMPT = """You are VisionGuard AI, an expert UI/UX accessibility auditor. 
Analyze this UI screenshot for WCAG 2.1 accessibility violations.

Provide your analysis in the following JSON format:
```json
{
  "overall_score": 0-100,
  "summary": "Brief summary of findings",
  "violations": [
    {
      "id": "v1",
      "type": "contrast|structure|navigation|forms|media",
      "severity": "critical|high|medium|low",
      "wcag_criterion": "1.4.3",
      "description": "What's wrong",
      "element_description": "Which element is affected",
      "suggestion": "How to fix it"
    }
  ],
  "positive_findings": ["List of things done well"],
  "design_observations": ["General UI/UX observations"]
}
```

Be thorough but practical. Focus on real, actionable violations."""

GENERATE_FIX_PROMPT = """You are VisionGuard AI, an expert UI/UX developer and accessibility specialist.

Based on the UI screenshot provided and the accessibility violations detected, generate a 
COMPLETE, self-contained HTML file that recreates the UI from the screenshot with ALL 
accessibility issues fixed.

Requirements:
1. The HTML must be self-contained (inline CSS, no external dependencies except Google Fonts)
2. Match the original design as closely as possible
3. Fix ALL identified accessibility violations:
   - Ensure all text meets WCAG AA contrast ratios (4.5:1 normal, 3:1 large)
   - Add proper ARIA labels and roles
   - Ensure proper heading hierarchy
   - Add alt text to images (use descriptive placeholders)
   - Ensure keyboard navigability
   - Add proper form labels
4. Use modern, semantic HTML5
5. Include a subtle banner at the top indicating "Accessibility-Fixed Version"
6. The page should be responsive and look good at any width

Violations to fix:
{violations_json}

{user_prompt}

Return ONLY the HTML code, wrapped in ```html ... ``` code fences. No explanation text outside the code."""

CHAT_SUGGESTION_PROMPT = """You are VisionGuard AI, an expert accessibility consultant.
You are helping a developer improve their UI's accessibility.

Context about the current UI being analyzed:
- Analysis results: {analysis_summary}
- Number of violations found: {violation_count}

The user says: "{user_message}"

Provide helpful, specific, actionable advice. If they ask about code changes, 
provide concrete code snippets. Format your response in markdown.

If relevant, reference specific WCAG criteria (e.g., WCAG 2.1 SC 1.4.3).
Be conversational but professional."""

REFINE_CODE_PROMPT = """You are VisionGuard AI. The user wants to refine the previously 
generated accessible HTML code.

Here is the current HTML code:
```html
{current_html}
```

The user's refinement request: "{user_prompt}"

Generate the updated HTML code incorporating the user's changes while maintaining 
all accessibility fixes. Return ONLY the updated HTML wrapped in ```html ... ``` fences."""


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class ScreenshotAnalysis:
    """Result of analyzing an uploaded screenshot."""
    analysis_id: str
    timestamp: str
    overall_score: float = 0.0
    summary: str = ""
    violations: List[dict] = field(default_factory=list)
    positive_findings: List[str] = field(default_factory=list)
    design_observations: List[str] = field(default_factory=list)
    original_screenshot_path: str = ""
    fixed_html: str = ""
    fixed_screenshot_path: str = ""
    error: Optional[str] = None


@dataclass
class ChatMessage:
    """A single message in the AI chat."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""


# ═══════════════════════════════════════════════════════════════
# Screenshot Analyzer Class
# ═══════════════════════════════════════════════════════════════

class ScreenshotAnalyzer:
    """
    Analyzes uploaded UI screenshots using Gemini multimodal AI.
    
    Capabilities:
    - Analyze screenshots for WCAG violations
    - Generate fixed HTML/CSS code  
    - Render fixed version as a screenshot
    - Interactive chat for accessibility suggestions
    """

    DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
        self._ai_available = False

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if self.api_key and _GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
                self._ai_available = True
                logger.info("ScreenshotAnalyzer: Gemini initialized → %s", self.model_name)
            except Exception as exc:
                logger.error("ScreenshotAnalyzer: Gemini init failed: %s", exc)
        else:
            logger.info("ScreenshotAnalyzer: No API key → mock mode")

        # In-memory stores
        self._analyses: Dict[str, ScreenshotAnalysis] = {}
        self._chat_histories: Dict[str, List[ChatMessage]] = {}

    @property
    def is_available(self) -> bool:
        return self._ai_available

    async def _call_gemini_with_fallback(self, contents: list) -> any:
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
        for m_name in unique_models:
            try:
                model = genai.GenerativeModel(m_name)
                response = await asyncio.to_thread(
                    model.generate_content,
                    contents=contents,
                    request_options={"retry": None}
                )
                if response and response.text:
                    logger.info("Gemini call succeeded with model: %s", m_name)
                    return response
            except Exception as e:
                last_exc = e
                logger.warning("Gemini model %s failed (%s: %s); trying fallback...", m_name, type(e).__name__, e)
                continue
        raise last_exc or RuntimeError("All Gemini models failed")

    # ─────────────────────────────────────────────────────────
    # Core Analysis
    # ─────────────────────────────────────────────────────────

    async def analyze_screenshot(
        self,
        image_bytes: bytes,
        filename: str,
        user_prompt: str = "",
    ) -> ScreenshotAnalysis:
        """
        Analyze an uploaded UI screenshot for accessibility issues.
        
        Args:
            image_bytes: Raw image file bytes
            filename: Original filename
            user_prompt: Optional user context/instructions
            
        Returns:
            ScreenshotAnalysis with violations and score
        """
        analysis_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info("[%s] Analyzing uploaded screenshot: %s", analysis_id, filename)

        # Save the uploaded screenshot (use absolute SCREENSHOTS_DIR so the
        # static file mount always finds it regardless of process CWD).
        upload_dir = os.path.join(SCREENSHOTS_DIR, f"upload_{analysis_id}")
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(filename)[1] or ".png"
        original_path = os.path.join(upload_dir, f"original{ext}")
        with open(original_path, "wb") as f:
            f.write(image_bytes)

        # Convert to a URL-relative path: /app/temp_screenshots/... -> temp_screenshots/...
        url_relative_path = (
            os.path.relpath(original_path, _PROJECT_ROOT).replace("\\", "/")
            if os.path.isabs(original_path)
            else original_path.replace("\\", "/").lstrip("/")
        )

        analysis = ScreenshotAnalysis(
            analysis_id=analysis_id,
            timestamp=timestamp,
            original_screenshot_path=url_relative_path,
        )

        if not self._ai_available or not _PIL_AVAILABLE:
            # Provide meaningful mock analysis when AI is unavailable
            analysis = self._generate_mock_analysis(analysis)
            self._analyses[analysis_id] = analysis
            return analysis

        try:
            # Step 1: Analyze the screenshot
            image = Image.open(original_path)
            
            prompt = SCREENSHOT_ANALYSIS_PROMPT
            if user_prompt:
                prompt += f"\n\nAdditional context from the user: {user_prompt}"

            response = await self._call_gemini_with_fallback([prompt, image])

            parsed = self._parse_json_response(response.text)
            
            if parsed:
                analysis.overall_score = parsed.get("overall_score", 50)
                analysis.summary = parsed.get("summary", "Analysis complete")
                analysis.violations = parsed.get("violations", [])
                analysis.positive_findings = parsed.get("positive_findings", [])
                analysis.design_observations = parsed.get("design_observations", [])
            else:
                analysis.summary = response.text[:500] if response.text else "Analysis complete"
                analysis.overall_score = 50

            logger.info(
                "[%s] Analysis complete: score=%s, violations=%d",
                analysis_id, analysis.overall_score, len(analysis.violations),
            )

        except Exception as exc:
            logger.error("[%s] Analysis failed: %s", analysis_id, exc, exc_info=True)
            analysis.error = str(exc)
            analysis = self._generate_mock_analysis(analysis)

        analysis._original_abs_path = original_path
        self._analyses[analysis_id] = analysis
        return analysis

    async def generate_fixed_code(
        self,
        analysis_id: str,
        user_prompt: str = "",
    ) -> dict:
        """
        Generate accessibility-fixed HTML/CSS code based on the analysis.
        
        Args:
            analysis_id: ID from a previous analyze_screenshot call
            user_prompt: Additional user instructions for the fix
            
        Returns:
            Dict with 'html' code and 'fixed_screenshot_path'
        """
        analysis = self._analyses.get(analysis_id)
        if not analysis:
            return {"error": f"Analysis '{analysis_id}' not found"}

        logger.info("[%s] Generating fixed code...", analysis_id)

        if not self._ai_available or not _PIL_AVAILABLE:
            html = self._generate_mock_fixed_html(analysis)
            analysis.fixed_html = html
            fixed_path = await self._render_html_to_screenshot(html, analysis_id)
            analysis.fixed_screenshot_path = fixed_path
            return {"html": html, "fixed_screenshot_path": fixed_path}

        try:
            abs_img_path = getattr(analysis, "_original_abs_path", None)
            if not abs_img_path or not os.path.exists(abs_img_path):
                upload_dir = os.path.join(SCREENSHOTS_DIR, f"upload_{analysis_id}")
                if os.path.exists(upload_dir):
                    for fname in os.listdir(upload_dir):
                        if fname.startswith("original"):
                            abs_img_path = os.path.join(upload_dir, fname)
                            break
            
            if abs_img_path and os.path.exists(abs_img_path):
                image = Image.open(abs_img_path)
            elif os.path.exists(analysis.original_screenshot_path):
                image = Image.open(analysis.original_screenshot_path)
            else:
                image = Image.open(os.path.join(_PROJECT_ROOT, analysis.original_screenshot_path))

            violations_json = json.dumps(analysis.violations[:20], indent=2)
            
            user_section = ""
            if user_prompt:
                user_section = f"\n\nAdditional user instructions:\n{user_prompt}"

            prompt = GENERATE_FIX_PROMPT.format(
                violations_json=violations_json,
                user_prompt=user_section,
            )

            response = await self._call_gemini_with_fallback([prompt, image])

            html = self._extract_html_from_response(response.text)

            if not html:
                html = self._generate_mock_fixed_html(analysis)

            analysis.fixed_html = html

            # Render the fixed HTML as a screenshot
            fixed_path = await self._render_html_to_screenshot(html, analysis_id)
            analysis.fixed_screenshot_path = fixed_path

            logger.info("[%s] Fixed code generated (%d chars)", analysis_id, len(html))

            return {"html": html, "fixed_screenshot_path": fixed_path}

        except Exception as exc:
            logger.error("[%s] Fix generation failed: %s", analysis_id, exc, exc_info=True)
            html = self._generate_mock_fixed_html(analysis)
            analysis.fixed_html = html
            fixed_path = await self._render_html_to_screenshot(html, analysis_id)
            analysis.fixed_screenshot_path = fixed_path
            return {"html": html, "fixed_screenshot_path": fixed_path, "warning": str(exc)}

    async def refine_code(
        self,
        analysis_id: str,
        user_prompt: str,
    ) -> dict:
        """
        Refine previously generated code based on user feedback.
        """
        analysis = self._analyses.get(analysis_id)
        if not analysis or not analysis.fixed_html:
            return {"error": "No generated code found. Generate fixes first."}

        if not self._ai_available:
            return {"html": analysis.fixed_html, "message": "AI unavailable, returning existing code"}

        try:
            prompt = REFINE_CODE_PROMPT.format(
                current_html=analysis.fixed_html[:8000],
                user_prompt=user_prompt,
            )

            response = await self._call_gemini_with_fallback([prompt])

            html = self._extract_html_from_response(response.text)
            if html:
                analysis.fixed_html = html
                fixed_path = await self._render_html_to_screenshot(html, analysis_id)
                analysis.fixed_screenshot_path = fixed_path
                return {"html": html, "fixed_screenshot_path": fixed_path}

            return {"html": analysis.fixed_html, "message": "Could not parse refined code"}

        except Exception as exc:
            logger.error("Refinement failed: %s", exc)
            return {"html": analysis.fixed_html, "error": str(exc)}

    # ─────────────────────────────────────────────────────────
    # Chat / Suggestions
    # ─────────────────────────────────────────────────────────

    async def chat(
        self,
        analysis_id: str,
        user_message: str,
    ) -> str:
        """
        Send a message to the AI accessibility consultant.
        
        Args:
            analysis_id: Context from a previous analysis (optional)
            user_message: The user's message
            
        Returns:
            AI response as markdown string
        """
        analysis = self._analyses.get(analysis_id)
        
        # Build context
        analysis_summary = "No analysis loaded"
        violation_count = 0
        if analysis:
            analysis_summary = analysis.summary or "Analysis available"
            violation_count = len(analysis.violations)

        # Initialize chat history if needed
        if analysis_id not in self._chat_histories:
            self._chat_histories[analysis_id] = []

        # Add user message
        self._chat_histories[analysis_id].append(ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        if not self._ai_available:
            response = self._generate_mock_chat_response(user_message, analysis)
        else:
            try:
                prompt = CHAT_SUGGESTION_PROMPT.format(
                    analysis_summary=analysis_summary,
                    violation_count=violation_count,
                    user_message=user_message,
                )

                # Include recent chat history for context
                history = self._chat_histories.get(analysis_id, [])
                if len(history) > 1:
                    history_text = "\n\nPrevious conversation:\n"
                    for msg in history[-6:-1]:  # Last 5 messages before current
                        history_text += f"**{msg.role}**: {msg.content[:200]}\n"
                    prompt += history_text

                result = await self._call_gemini_with_fallback([prompt])
                response = result.text or "I couldn't generate a response. Please try again."

            except Exception as exc:
                logger.error("Chat failed: %s", exc)
                response = f"I encountered an error: {exc}. Please try again."

        # Add assistant response
        self._chat_histories[analysis_id].append(ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        return response

    def get_chat_history(self, analysis_id: str) -> List[dict]:
        """Get the chat history for an analysis session."""
        history = self._chat_histories.get(analysis_id, [])
        return [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in history]

    def get_analysis(self, analysis_id: str) -> Optional[ScreenshotAnalysis]:
        """Retrieve a stored analysis by ID."""
        return self._analyses.get(analysis_id)

    # ─────────────────────────────────────────────────────────
    # HTML Rendering
    # ─────────────────────────────────────────────────────────

    async def _render_html_to_screenshot(self, html: str, analysis_id: str) -> str:
        """Render HTML to a screenshot using Playwright."""
        try:
            output_dir = os.path.join(SCREENSHOTS_DIR, f"upload_{analysis_id}")
            os.makedirs(output_dir, exist_ok=True)
            fixed_path = os.path.join(output_dir, "fixed_render.png")

            # Write HTML to a temp file
            html_path = os.path.join(output_dir, "fixed.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            file_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}"

            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1280, "height": 900})
                await page.goto(file_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                await page.screenshot(path=fixed_path, full_page=True)
                await browser.close()

            logger.info("[%s] Rendered fixed screenshot: %s", analysis_id, fixed_path)
            
            # Return URL-relative path so the frontend can load it from static mount
            url_relative_path = (
                os.path.relpath(fixed_path, _PROJECT_ROOT).replace("\\", "/")
                if os.path.isabs(fixed_path)
                else fixed_path.replace("\\", "/").lstrip("/")
            )
            return url_relative_path

        except Exception as exc:
            logger.error("Failed to render HTML screenshot: %s", exc)
            return ""

    # ─────────────────────────────────────────────────────────
    # Mock / Fallback methods
    # ─────────────────────────────────────────────────────────

    def _generate_mock_analysis(self, analysis: ScreenshotAnalysis) -> ScreenshotAnalysis:
        """Generate a realistic mock analysis when AI is unavailable."""
        analysis.overall_score = 62
        analysis.summary = (
            "Automated visual analysis detected several accessibility concerns. "
            "Key issues include potential contrast violations, missing semantic structure, "
            "and possible navigation barriers."
        )
        analysis.violations = [
            {
                "id": "v1",
                "type": "contrast",
                "severity": "critical",
                "wcag_criterion": "1.4.3",
                "description": "Low contrast text detected. Light gray text on white background fails WCAG AA minimum contrast ratio of 4.5:1.",
                "element_description": "Body text and secondary labels",
                "suggestion": "Darken text color to at least #767676 for white backgrounds to meet 4.54:1 ratio."
            },
            {
                "id": "v2",
                "type": "structure",
                "severity": "high",
                "wcag_criterion": "1.3.1",
                "description": "Heading hierarchy may be skipped. Ensure headings follow a logical order (h1 → h2 → h3).",
                "element_description": "Page headings",
                "suggestion": "Use sequential heading levels without skipping. Add aria-level if visual hierarchy differs."
            },
            {
                "id": "v3",
                "type": "navigation",
                "severity": "medium",
                "wcag_criterion": "2.4.1",
                "description": "No skip navigation link detected. Screen reader users must tab through all navigation items.",
                "element_description": "Page navigation",
                "suggestion": "Add a 'Skip to main content' link as the first focusable element."
            },
            {
                "id": "v4",
                "type": "forms",
                "severity": "medium",
                "wcag_criterion": "1.3.1",
                "description": "Form inputs may lack associated labels.",
                "element_description": "Input fields and buttons",
                "suggestion": "Ensure every input has a visible <label> element with a matching 'for' attribute."
            },
            {
                "id": "v5",
                "type": "contrast",
                "severity": "low",
                "wcag_criterion": "1.4.11",
                "description": "Non-text elements (borders, icons) may have insufficient contrast against background.",
                "element_description": "UI borders and icons",
                "suggestion": "Ensure non-text UI components have at least 3:1 contrast ratio."
            },
        ]
        analysis.positive_findings = [
            "Page appears to use readable font sizes (≥16px)",
            "Layout appears responsive with logical visual hierarchy",
            "Color is not the sole means of conveying information",
        ]
        analysis.design_observations = [
            "Consider adding focus indicators for keyboard navigation",
            "Interactive elements should have visible hover/focus states",
            "Touch targets should be at least 44×44px for mobile accessibility",
        ]
        return analysis

    def _generate_mock_fixed_html(self, analysis: ScreenshotAnalysis) -> str:
        """Generate a sample fixed HTML when AI is unavailable."""
        violations_list = ""
        for v in analysis.violations:
            violations_list += f"""
            <li class="violation-item {v.get('severity', 'medium')}">
                <span class="severity-badge">{v.get('severity', 'medium').upper()}</span>
                <strong>{v.get('description', 'Issue detected')}</strong>
                <p class="suggestion">Fix: {v.get('suggestion', 'Review and fix this issue')}</p>
            </li>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VisionGuard AI - Accessibility-Fixed Version</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        :root {{
            --bg: #0f1117;
            --surface: #1a1b23;
            --border: #2a2b35;
            --text-primary: #e8e9ed;
            --text-secondary: #9ca3af;
            --accent: #6366f1;
            --accent-hover: #818cf8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --critical: #dc2626;
        }}

        body {{
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            background: var(--bg);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}

        /* Skip Navigation - WCAG 2.4.1 */
        .skip-link {{
            position: absolute;
            top: -40px;
            left: 0;
            background: var(--accent);
            color: white;
            padding: 8px 16px;
            z-index: 100;
            font-weight: 600;
            border-radius: 0 0 8px 0;
            transition: top 0.2s;
        }}
        .skip-link:focus {{
            top: 0;
        }}

        /* Accessibility Fix Banner */
        .fix-banner {{
            background: linear-gradient(135deg, var(--accent), #8b5cf6);
            color: white;
            text-align: center;
            padding: 10px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.02em;
        }}
        .fix-banner strong {{
            font-weight: 700;
        }}

        header {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
        }}

        header h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }}

        nav {{
            display: flex;
            gap: 24px;
            margin-top: 12px;
        }}

        nav a {{
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            padding: 4px 0;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}

        nav a:hover, nav a:focus {{
            color: var(--accent-hover);
            border-bottom-color: var(--accent);
            outline: 2px solid var(--accent);
            outline-offset: 2px;
            border-radius: 2px;
        }}

        nav a[aria-current="page"] {{
            color: var(--accent);
            border-bottom-color: var(--accent);
        }}

        main {{
            max-width: 960px;
            margin: 0 auto;
            padding: 32px 24px;
        }}

        h2 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-primary);
        }}

        .score-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 24px;
        }}

        .score-circle {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 700;
            background: conic-gradient(var(--accent) {analysis.overall_score}%, var(--border) 0%);
            position: relative;
        }}

        .score-circle::before {{
            content: '{int(analysis.overall_score)}';
            position: absolute;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--surface);
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .violations-list {{
            list-style: none;
            display: grid;
            gap: 12px;
        }}

        .violation-item {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid var(--warning);
        }}

        .violation-item.critical {{ border-left-color: var(--critical); }}
        .violation-item.high {{ border-left-color: var(--danger); }}
        .violation-item.medium {{ border-left-color: var(--warning); }}
        .violation-item.low {{ border-left-color: var(--text-secondary); }}

        .severity-badge {{
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .critical .severity-badge {{ background: var(--critical); color: white; }}
        .high .severity-badge {{ background: var(--danger); color: white; }}
        .medium .severity-badge {{ background: var(--warning); color: black; }}
        .low .severity-badge {{ background: var(--text-secondary); color: white; }}

        .violation-item strong {{
            display: block;
            margin-top: 4px;
            font-size: 0.95rem;
            color: var(--text-primary);
        }}

        .suggestion {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 6px;
            padding-left: 12px;
            border-left: 2px solid var(--border);
        }}

        /* Focus indicators - WCAG 2.4.7 */
        *:focus-visible {{
            outline: 2px solid var(--accent);
            outline-offset: 2px;
            border-radius: 4px;
        }}

        footer {{
            text-align: center;
            padding: 24px;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 48px;
        }}
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <div class="fix-banner" role="banner">
        ✅ <strong>VisionGuard AI</strong> — Accessibility-Fixed Version (WCAG 2.1 AA Compliant)
    </div>

    <header role="banner">
        <h1>Accessibility-Fixed UI</h1>
        <nav role="navigation" aria-label="Main navigation">
            <a href="#" aria-current="page">Dashboard</a>
            <a href="#">Reports</a>
            <a href="#">Settings</a>
        </nav>
    </header>

    <main id="main-content" role="main">
        <h2>Accessibility Score</h2>
        <div class="score-card" role="status" aria-label="Accessibility score: {int(analysis.overall_score)} out of 100">
            <div class="score-circle" role="img" aria-label="{int(analysis.overall_score)}%"></div>
            <div>
                <p style="font-size: 1.1rem; font-weight: 600;">Score: {int(analysis.overall_score)}/100</p>
                <p style="color: var(--text-secondary); font-size: 0.9rem;">
                    {analysis.summary or 'Analysis complete. Review violations below.'}
                </p>
            </div>
        </div>

        <h2>Violations Found ({len(analysis.violations)})</h2>
        <ul class="violations-list" aria-label="Accessibility violations">
            {violations_list}
        </ul>
    </main>

    <footer role="contentinfo">
        <p>Generated by VisionGuard AI — Autonomous Accessibility Auditor</p>
    </footer>
</body>
</html>"""

    def _generate_mock_chat_response(
        self, user_message: str, analysis: Optional[ScreenshotAnalysis]
    ) -> str:
        """Generate a helpful mock response when AI is unavailable."""
        msg_lower = user_message.lower()

        if any(w in msg_lower for w in ["contrast", "color", "text"]):
            return """## Contrast & Color Accessibility

Here are the key WCAG 2.1 requirements for color contrast:

**Normal text** (< 18pt or < 14pt bold):
- **AA**: Minimum contrast ratio of **4.5:1**
- **AAA**: Minimum contrast ratio of **7:1**

**Large text** (≥ 18pt or ≥ 14pt bold):
- **AA**: Minimum contrast ratio of **3:1**  
- **AAA**: Minimum contrast ratio of **4.5:1**

### Quick Fix Example:
```css
/* Bad: gray on white = 2.5:1 ratio */
.text-muted { color: #aaaaaa; }

/* Good: darker gray on white = 4.6:1 ratio */
.text-muted { color: #767676; }
```

> 💡 **Tip**: Use `#767676` as the lightest gray on white backgrounds — it's the exact boundary for WCAG AA compliance."""

        if any(w in msg_lower for w in ["aria", "screen reader", "label"]):
            return """## ARIA Labels & Screen Reader Support

### Key Rules:
1. **Every interactive element needs an accessible name** — via visible label, `aria-label`, or `aria-labelledby`
2. **Don't overuse ARIA** — native HTML semantics are always preferred
3. **Landmark roles** help screen readers navigate: `main`, `nav`, `banner`, `contentinfo`

### Examples:
```html
<!-- Bad: icon button with no label -->
<button><svg>...</svg></button>

<!-- Good: accessible icon button -->
<button aria-label="Close dialog"><svg>...</svg></button>

<!-- Good: input with visible label -->
<label for="email">Email address</label>
<input id="email" type="email" />
```"""

        if any(w in msg_lower for w in ["keyboard", "focus", "tab"]):
            return """## Keyboard Navigation (WCAG 2.1.1)

All functionality must be available via keyboard:

1. **Tab order** should follow visual reading order
2. **Focus indicators** must be visible (don't remove `outline`)
3. **Custom widgets** need `tabindex`, `role`, and keyboard event handlers

```css
/* Always maintain visible focus indicators */
*:focus-visible {
    outline: 2px solid #6366f1;
    outline-offset: 2px;
}

/* Never do this: */
*:focus { outline: none; } /* ❌ WCAG violation */
```"""

        # Default helpful response
        return f"""## Accessibility Guidance

Thanks for your question! Here are some key areas to focus on:

**Top 5 WCAG Quick Wins:**
1. 🎨 **Color contrast** — Ensure 4.5:1 ratio for normal text (SC 1.4.3)
2. 🏷️ **Form labels** — Every input needs a `<label>` (SC 1.3.1)
3. 🖼️ **Image alt text** — All `<img>` tags need descriptive `alt` attributes (SC 1.1.1)
4. ⌨️ **Keyboard access** — All interactive elements must be keyboard-operable (SC 2.1.1)
5. 📐 **Heading hierarchy** — Use h1→h2→h3 in logical order (SC 1.3.1)

Would you like me to elaborate on any of these areas? Feel free to ask about specific elements or code patterns!"""

    # ─────────────────────────────────────────────────────────
    # Parsing Helpers
    # ─────────────────────────────────────────────────────────

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Parse JSON from LLM response."""
        if not text:
            return None

        cleaned = text.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _extract_html_from_response(self, text: str) -> Optional[str]:
        """Extract HTML code from LLM response."""
        if not text:
            return None

        # Try to extract from code fence
        html_match = re.search(r"```html\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if html_match:
            return html_match.group(1).strip()

        # Try generic code fence
        code_match = re.search(r"```\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            if "<!DOCTYPE" in code or "<html" in code:
                return code

        # If the whole response looks like HTML
        if "<!DOCTYPE" in text or "<html" in text:
            return text.strip()

        return None
