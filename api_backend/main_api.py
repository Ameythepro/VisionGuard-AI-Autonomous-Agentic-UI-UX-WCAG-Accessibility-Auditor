"""
VisionGuard AI - Main API Gateway
===================================
Asynchronous FastAPI backend that orchestrates the full audit pipeline:
1. Accepts a URL from the user.
2. Checks Redis cache for existing results.
3. Dispatches the BrowserEngine to capture screenshots + DOM.
4. Returns structured audit results.

Run with: uvicorn api_backend.main_api:app --reload --port 8000
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_automation.browser_engine import BrowserEngine, AuditCapture
from browser_automation.sandbox_injector import SandboxInjector
from api_backend.redis_cache import RedisCache

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

# Shared service instances
browser_engine = BrowserEngine(headless=True)
sandbox_injector = SandboxInjector(headless=True)
cache = RedisCache()

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
        
        # Build the result payload
        result = {
            "audit_id": audit_id,
            "url": url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_seconds": audit_capture.duration_seconds,
            "viewports_captured": list(audit_capture.captures.keys()),
            "viewports_failed": audit_capture.errors,
            "screenshots": {
                name: capture.screenshot_path 
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
        }
        
        # Cache the result
        cache.cache_audit_result(url, result)
        
        # Store in memory for retrieval by audit_id
        audit_store[audit_id] = result
        
        logger.info(
            f"[{audit_id}] Audit completed: "
            f"{len(audit_capture.captures)} viewports, "
            f"{len(computed_styles)} styled elements"
        )
        
        return AuditStatusResponse(
            audit_id=audit_id,
            status="completed",
            url=url,
            message=f"Audit completed successfully. {len(audit_capture.captures)} viewports captured.",
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


# ─────────────────────────────────────────────
# Startup / Shutdown Events
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("VisionGuard AI API starting up...")
    logger.info(f"Redis available: {cache.is_available()}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("VisionGuard AI API shutting down...")
