"""
VisionGuard AI - Main API Gateway
===================================
Asynchronous FastAPI backend that orchestrates the full audit pipeline:
1. Accepts a URL from the user.
2. Checks Redis cache for existing results.
3. Dispatches the BrowserEngine to capture screenshots + DOM.
4. Runs deterministic WCAG 2.1 accessibility checks (Role 3).
5. Returns structured audit results with accessibility scores.

Run with: uvicorn api_backend.main_api:app --reload --port 8000
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, Field

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_automation.browser_engine import BrowserEngine, AuditCapture
from browser_automation.sandbox_injector import SandboxInjector
from api_backend.redis_cache import RedisCache

# ── Role 3: DOM & Accessibility Engine ────────
from dom_accessibility.dom_parser import DOMParser
from dom_accessibility.wcag_checker import audit_computed_styles
from dom_accessibility.ast_extractor import ASTExtractor

# ── Role 1: AI Agent Engine (Gemini multimodal) ────────
from ai_engine.agent_engine import VisionGuardAgent

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("visionguard.api")


# ─────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(
    title="VisionGuard AI API",
    description=(
        "Autonomous Agentic UI/UX & WCAG Accessibility Auditor. "
        "Captures multi-viewport screenshots, extracts computed styles, "
        "and runs deterministic WCAG 2.1 accessibility checks."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow Streamlit frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("temp_screenshots", exist_ok=True)
app.mount("/temp_screenshots", StaticFiles(directory="temp_screenshots"), name="temp_screenshots")

# Shared service instances
browser_engine = BrowserEngine(headless=True)
sandbox_injector = SandboxInjector(headless=True)
cache = RedisCache()
ai_agent = VisionGuardAgent()  # Reads GOOGLE_API_KEY from .env automatically

# In-memory store for audit results (keyed by audit_id)
audit_store: dict = {}


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────
class AuditRequest(BaseModel):
    """Request body for initiating a URL audit."""
    url: str = Field(..., description="The target URL to audit", examples=["https://example.com"])


class AuditStatusResponse(BaseModel):
    """Response when an audit is initiated or queried."""
    audit_id: str
    status: str  # "processing" | "completed" | "failed"
    url: str
    message: str
    result: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    redis_connected: bool


class PatchRequest(BaseModel):
    """Request body for CSS sandbox patch verification."""
    url: str = Field(..., description="Target URL")
    css_patch: str = Field(..., description="CSS patch to inject and verify")
    viewport: str = Field(default="desktop_1080p", description="Viewport preset name")


class AccessibilityAuditRequest(BaseModel):
    """Request body for standalone accessibility auditing."""
    html_source: str = Field(default="", description="Raw HTML source to analyze for DOM violations")
    computed_styles: List[dict] = Field(default_factory=list, description="Computed styles from browser (same format as BrowserEngine.extract_computed_styles)")
    url: str = Field(default="", description="URL for reporting purposes")
    css_source: str = Field(default="", description="Optional raw CSS to extract and validate")


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify API and dependency status."""
    return HealthResponse(
        status="healthy",
        service="VisionGuard AI Backend",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        redis_connected=cache.is_available(),
    )


@app.post("/audit-url", response_model=AuditStatusResponse)
async def audit_url(request: AuditRequest):
    """
    Initiates a full accessibility audit for a given URL.
    
    Pipeline:
    1. Check Redis cache for recent results.
    2. If cache miss, launch BrowserEngine to capture all viewports.
    3. Extract computed CSS styles from the rendered page.
    4. Store the raw capture data for downstream AI processing.
    5. Return the audit results.
    """
    url = request.url.strip()
    
    # Validate URL format
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Must start with http:// or https://"
        )

    audit_id = str(uuid.uuid4())[:8]
    logger.info(f"[{audit_id}] Audit requested for: {url}")

    # --- Check cache ---
    cached = cache.get_cached_audit(url)
    if cached:
        logger.info(f"[{audit_id}] Returning cached result")
        return AuditStatusResponse(
            audit_id=audit_id,
            status="completed",
            url=url,
            message="Returned cached audit result",
            result=cached,
        )

    # --- Run the browser engine ---
    try:
        output_dir = os.path.join(
            "temp_screenshots",
            f"audit_{audit_id}_{int(time.time())}"
        )
        
        # Step 1: Capture screenshots + DOM across all viewports
        audit_capture: AuditCapture = await browser_engine.capture_page(url, output_dir)
        
        # Step 2: Extract computed CSS styles for WCAG analysis
        computed_styles = await browser_engine.extract_computed_styles(url)
        
        # ── Step 3: Role 3 — Run WCAG math on computed styles ──
        wcag_result = audit_computed_styles(computed_styles, url=url)
        
        # ── Step 4: Role 3 — Run DOM parser on captured HTML ──
        first_capture = next(iter(audit_capture.captures.values()), None)
        dom_parser = DOMParser()
        dom_result = dom_parser.analyze(
            first_capture.html_source if first_capture else "",
            url=url,
        )
        
        # ── Step 5: Role 3 — Build unified diagnostic ──
        ast_extractor = ASTExtractor()
        css_rules = []
        if first_capture and first_capture.html_source:
            css_rules = ast_extractor.extract_css_from_html(first_capture.html_source)
        
        unified_diagnostic = ast_extractor.build_unified_diagnostic(
            dom_result=dom_result,
            wcag_result=wcag_result,
            css_rules=css_rules,
            url=url,
        )
        
        # Build the result payload
        result = {
            "audit_id": audit_id,
            "url": url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_seconds": audit_capture.duration_seconds,
            "viewports_captured": list(audit_capture.captures.keys()),
            "viewports_failed": audit_capture.errors,
            "screenshots": {
                name: capture.screenshot_path.replace("\\", "/")
                for name, capture in audit_capture.captures.items()
            },
            "page_title": next(iter(audit_capture.captures.values())).page_title 
                if audit_capture.captures else "Unknown",
            "computed_styles_count": len(computed_styles),
            "computed_styles": computed_styles,
            "html_sources": {
                name: f"Captured ({len(capture.html_source)} chars)"
                for name, capture in audit_capture.captures.items()
            },
            # ── Role 3 accessibility results ──
            "accessibility_score": wcag_result.overall_score,
            "wcag_violations": [asdict(v) for v in wcag_result.contrast_violations],
            "wcag_violation_counts": {
                "total": wcag_result.total_violations,
                "critical": wcag_result.critical_count,
                "high": wcag_result.high_count,
                "medium": wcag_result.medium_count,
                "low": wcag_result.low_count,
            },
            "dom_violations": [asdict(v) for v in dom_result.violations],
            "dom_violation_counts": {
                "total": dom_result.total_violations,
                "critical": dom_result.critical_count,
                "high": dom_result.high_count,
                "medium": dom_result.medium_count,
                "low": dom_result.low_count,
            },
            "dom_metadata": {
                "has_lang": dom_result.has_lang_attribute,
                "has_title": dom_result.has_page_title,
                "dark_mode_supported": dom_result.supports_dark_mode,
                "heading_structure": dom_result.heading_structure,
                "total_images": dom_result.total_images,
                "images_missing_alt": dom_result.images_missing_alt,
                "total_links": dom_result.total_links,
                "links_missing_text": dom_result.links_missing_text,
                "total_form_inputs": dom_result.total_form_inputs,
                "inputs_missing_labels": dom_result.inputs_missing_labels,
            },
            "unified_diagnostic": ast_extractor.diagnostic_to_dict(unified_diagnostic),
            # ── AI mode info ──
            "ai_mode": ai_agent.mode,
        }
        
        # ── Role 1: AI-Enhanced Analysis (Gemini Multimodal) ──
        if ai_agent._ai_available:
            try:
                logger.info(f"[{audit_id}] Running Gemini AI analysis...")
                # Find a screenshot to send to Gemini
                screenshot_path = result["screenshots"].get(
                    "desktop_1080p",
                    next(iter(result["screenshots"].values()), None),
                )
                # Build violations list in the format agent_engine expects
                from ai_engine.agent_engine import run_wcag_audit as agent_wcag_audit
                agent_violations, _ = agent_wcag_audit(computed_styles)
                
                # Step 3: AI multimodal analysis
                if screenshot_path and os.path.exists(screenshot_path):
                    ai_analysis = await ai_agent._analyze_with_llm(
                        screenshot_path=screenshot_path,
                        violations=agent_violations,
                        computed_styles=computed_styles,
                        url=url,
                        page_title=result.get("page_title", ""),
                    )
                    result["ai_analysis"] = ai_analysis
                    logger.info(f"[{audit_id}] Gemini AI analysis complete!")
                
                # Step 4: AI-generated CSS patches
                if agent_violations:
                    patches_data = await ai_agent._generate_patches(agent_violations, url)
                    result["ai_patches"] = patches_data.get("patches", [])
                    result["ai_combined_patch"] = patches_data.get("combined_patch", "")
                    logger.info(f"[{audit_id}] AI generated {len(result['ai_patches'])} CSS patches")
                else:
                    result["ai_patches"] = []
                    result["ai_combined_patch"] = ""
                    
            except Exception as ai_err:
                logger.warning(f"[{audit_id}] AI analysis failed (non-fatal): {ai_err}")
                result["ai_analysis"] = {"error": str(ai_err)}
                result["ai_patches"] = []
                result["ai_combined_patch"] = ""
        else:
            result["ai_analysis"] = None
            result["ai_patches"] = []
            result["ai_combined_patch"] = ""
        
        # Cache the result
        cache.cache_audit_result(url, result)
        
        # Store in memory for retrieval by audit_id
        audit_store[audit_id] = result
        
        logger.info(
            f"[{audit_id}] Audit completed: "
            f"{len(audit_capture.captures)} viewports, "
            f"{len(computed_styles)} styled elements, "
            f"accessibility_score={wcag_result.overall_score}%, "
            f"wcag_violations={wcag_result.total_violations}, "
            f"dom_violations={dom_result.total_violations}"
        )
        
        return AuditStatusResponse(
            audit_id=audit_id,
            status="completed",
            url=url,
            message=(
                f"Audit completed successfully. "
                f"{len(audit_capture.captures)} viewports captured. "
                f"Accessibility score: {wcag_result.overall_score}%. "
                f"{wcag_result.total_violations} contrast violations, "
                f"{dom_result.total_violations} DOM violations found."
            ),
            result=result,
        )
        
    except Exception as e:
        logger.error(f"[{audit_id}] Audit failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Audit failed: {type(e).__name__}: {str(e)}"
        )


@app.get("/audit/{audit_id}", response_model=AuditStatusResponse)
async def get_audit_result(audit_id: str):
    """Retrieve the result of a previously completed audit by ID."""
    if audit_id not in audit_store:
        raise HTTPException(status_code=404, detail=f"Audit '{audit_id}' not found")
    
    result = audit_store[audit_id]
    return AuditStatusResponse(
        audit_id=audit_id,
        status="completed",
        url=result["url"],
        message="Audit result retrieved",
        result=result,
    )


@app.post("/sandbox/verify-patch")
async def verify_css_patch(request: PatchRequest):
    """
    Applies a CSS patch to a URL in a sandboxed browser and captures
    before/after screenshots for the AI reflection loop.
    """
    try:
        sandbox_result = await sandbox_injector.apply_and_verify(
            url=request.url,
            css_patch=request.css_patch,
            viewport_name=request.viewport,
        )
        
        return {
            "success": sandbox_result.success,
            "error": sandbox_result.error,
            "original_screenshot": sandbox_result.original_screenshot,
            "patched_screenshot": sandbox_result.patched_screenshot,
            "viewport": sandbox_result.viewport_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/accessibility")
async def standalone_accessibility_audit(request: AccessibilityAuditRequest):
    """
    Standalone accessibility audit endpoint.

    Accepts raw HTML and/or computed styles directly (without needing
    a live URL + browser capture). Useful for:
    - Testing individual HTML snippets
    - CI/CD pipeline integration
    - The AI engine to validate its own generated HTML

    Returns WCAG contrast violations, DOM structural violations,
    accessibility score, and optional CSS validation.
    """
    try:
        results = {
            "url": request.url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # ── WCAG contrast check on computed styles ──
        if request.computed_styles:
            wcag_result = audit_computed_styles(
                request.computed_styles, url=request.url
            )
            results["accessibility_score"] = wcag_result.overall_score
            results["wcag_violations"] = [
                asdict(v) for v in wcag_result.contrast_violations
            ]
            results["wcag_summary"] = {
                "total_elements_checked": wcag_result.total_elements_checked,
                "total_violations": wcag_result.total_violations,
                "critical": wcag_result.critical_count,
                "high": wcag_result.high_count,
                "medium": wcag_result.medium_count,
                "low": wcag_result.low_count,
            }
        else:
            results["accessibility_score"] = 100.0
            results["wcag_violations"] = []
            results["wcag_summary"] = {
                "total_elements_checked": 0,
                "total_violations": 0,
                "critical": 0, "high": 0, "medium": 0, "low": 0,
            }

        # ── DOM structural checks on HTML source ──
        if request.html_source:
            dom_parser = DOMParser()
            dom_result = dom_parser.analyze(request.html_source, url=request.url)
            results["dom_violations"] = [asdict(v) for v in dom_result.violations]
            results["dom_summary"] = {
                "total_violations": dom_result.total_violations,
                "critical": dom_result.critical_count,
                "high": dom_result.high_count,
                "medium": dom_result.medium_count,
                "low": dom_result.low_count,
                "has_lang": dom_result.has_lang_attribute,
                "has_title": dom_result.has_page_title,
                "dark_mode_supported": dom_result.supports_dark_mode,
                "heading_structure": dom_result.heading_structure,
                "total_images": dom_result.total_images,
                "images_missing_alt": dom_result.images_missing_alt,
                "total_links": dom_result.total_links,
                "links_missing_text": dom_result.links_missing_text,
                "total_form_inputs": dom_result.total_form_inputs,
                "inputs_missing_labels": dom_result.inputs_missing_labels,
            }
        else:
            results["dom_violations"] = []
            results["dom_summary"] = {"total_violations": 0}

        # ── CSS validation (optional) ──
        if request.css_source:
            ast_extractor = ASTExtractor()
            validation = ast_extractor.validate_css_patch(request.css_source)
            results["css_validation"] = {
                "is_valid": validation.is_valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "rules_parsed": len(validation.parsed_rules),
            }

        logger.info(
            f"Standalone accessibility audit: "
            f"score={results['accessibility_score']}%, "
            f"wcag_violations={len(results['wcag_violations'])}, "
            f"dom_violations={len(results['dom_violations'])}"
        )

        return results

    except Exception as e:
        logger.error(f"Standalone accessibility audit failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Accessibility audit failed: {type(e).__name__}: {str(e)}"
        )


@app.post("/audit/validate-css")
async def validate_css_patch_endpoint(css_patch: str = ""):
    """
    Validate a CSS patch string for syntax correctness and security.

    This endpoint is used by the AI engine to verify its generated
    CSS patches before injecting them into the browser sandbox.
    """
    try:
        ast_extractor = ASTExtractor()
        validation = ast_extractor.validate_css_patch(css_patch)
        return {
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "rules_parsed": len(validation.parsed_rules),
            "parsed_selectors": [r.selector for r in validation.parsed_rules],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# Startup / Shutdown Events
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("VisionGuard AI API starting up...")
    logger.info(f"Redis available: {cache.is_available()}")
    logger.info(f"AI mode: {ai_agent.mode} (Gemini={'ON' if ai_agent._ai_available else 'OFF'})")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("VisionGuard AI API shutting down...")
