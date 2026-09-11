# VisionGuard AI Implementation Roadmap

This document outlines the strategic implementation plan for VisionGuard AI to ensure maximum success, high code quality, and proper integration across the microservices architecture.

## User Review Required

> [!IMPORTANT]
> Please review this phased roadmap. If you agree with this approach, your team can begin executing Phase 1 immediately in their respective branches. Let me know if you want to adjust the priorities or start coding a specific module right now.

## Strategic Approach

To succeed, we must avoid "integration hell" by building the system from the **bottom up**. We will establish the core automation and data parsing capabilities first, then layer the AI intelligence on top, and finally connect the user interface.

We will execute in 4 distinct phases.

---

## Phase 1: The Foundation (Data Acquisition)
**Goal:** Be able to programmatically open a website, take a screenshot, and extract the raw HTML/DOM.

### `feature-automation` (Browser Engineer)
- **Target:** `browser_automation/browser_engine.py` & `viewport_manager.py`
- **Tasks:**
  - Implement Playwright to launch Chromium in headless mode.
  - Create functions to navigate to a URL and wait for network idle.
  - Implement viewport resizing (Desktop, Tablet, Mobile).
  - Capture full-page screenshots and save them temporarily.

### `feature-backend-ui` (Backend Lead)
- **Target:** `api_backend/main_api.py`
- **Tasks:**
  - Initialize the FastAPI app.
  - Create a health-check endpoint (`GET /health`).
  - Create the main auditing endpoint (`POST /audit-url`) that accepts a URL payload.

---

## Phase 2: The Logic (Accessibility & Parsing)
**Goal:** Parse the extracted DOM and mathematically verify accessibility rules.

### `feature-accessibility` (Accessibility Engineer)
- **Target:** `dom_accessibility/dom_parser.py` & `wcag_checker.py`
- **Tasks:**
  - Use `beautifulsoup4` to extract text nodes, buttons, and image tags.
  - Extract computed CSS styles (specifically text color and background color).
  - Implement the WCAG 2.1 Relative Luminance formula to calculate contrast ratios.
  - Return a structured JSON of accessibility violations.

---

## Phase 3: The Brain (AI Orchestration)
**Goal:** Connect the Multimodal LLM to analyze the screenshots and the accessibility JSON.

### `feature-ai-agent` (AI Architect)
- **Target:** `ai_engine/agent_engine.py` & `prompt_templates.py`
- **Tasks:**
  - Initialize `langchain-google-genai` (Gemini) or Claude.
  - Define system prompts for the "UI/UX Reviewer" and "Accessibility Fixer" personas.
  - Implement the reflection loop: The agent suggests a CSS patch, we theoretically apply it, and verify if it fixes the contrast issue.
  - Format the final output as a comprehensive audit report.

---

## Phase 4: The Interface (Integration & UI)
**Goal:** Tie all microservices together and provide a beautiful dashboard.

### `feature-backend-ui` (Backend & UI Lead)
- **Target:** `frontend_ui/app_dashboard.py` & `api_backend/redis_cache.py`
- **Tasks:**
  - Build the Streamlit dashboard with a URL input field.
  - Implement the `streamlit-image-comparison` slider to show the "Before" (original screenshot) and "After" (screenshot with AI's CSS patches injected).
  - Integrate Redis to cache reports for previously audited URLs to save LLM tokens and API costs.

## Verification Plan

### Automated Tests
- We will write `pytest` unit tests for the WCAG math logic (`tests/test_wcag_math.py`) to ensure contrast calculations are 100% accurate.
- We will test the Playwright engine (`tests/test_playwright.py`) against standard test pages.

### Manual Verification
- We will run the Streamlit dashboard locally and audit a known "bad" website (e.g., low contrast text, overlapping divs) and verify that the AI correctly identifies and patches the issues.
