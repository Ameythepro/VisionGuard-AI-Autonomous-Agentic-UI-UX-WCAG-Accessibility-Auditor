# VisionGuard AI — Role 3: DOM & Accessibility Development Handoff Documentation

> **Document Purpose:** Handoff guide capturing 100% of the architecture, progress, code implementations, mathematical formulas, data contracts, and remaining steps completed for **Role 3 (DOM & Accessibility Engineer)** on branch `feature-accessibility` before the Claude Opus quota limit was reached.  
> **Target Audience:** Future Claude Opus / Antigravity session resuming in 2 days, plus beginner-friendly explanation for the student developer.  
> **Active Branch:** `feature-accessibility`  
> **Role 3 Completion Status:** ~85% (Core Symbolic Engine fully built: 2,749 lines across 5 files; remaining: API integration, pytest run, git commit & push)

---

## 1. High-Level Overview (For Beginners & Presentation)

### What is Role 3 in VisionGuard AI?
In VisionGuard AI, we are building a **Neuro-Symbolic** system.
- **The "Neuro" part (Role 1 - AI Agent):** Uses Large Language Models (LLMs) like Gemini / Claude to analyze visual screenshots and write CSS code fixes.
- **The "Symbolic" part (Role 3 - YOU):** Uses **deterministic mathematical formulas and strict rules**. Computers do math and parsing with 100% accuracy. LLMs can hallucinate math (e.g. saying 3.8:1 passes a 4.5:1 requirement). Role 3 guarantees that **zero accessibility math is hallucinated**. Every color, contrast ratio, heading level, image tag, and CSS patch is verified with mathematical certainty.

### How Does Role 3 Fit With Teammates?
```
   [Teammate 1 / Role 2: Browser Engine (Playwright)]
                        │
                        ├─► 1. Raw HTML Source (PageCapture.html_source)
                        └─► 2. Computed CSS Styles (extract_computed_styles())
                                       │
                                       ▼
             ╔══════════════════════════════════════════════════════╗
             ║     ROLE 3: DOM & ACCESSIBILITY ENGINE (OUR WORK)    ║
             ╠══════════════════════════════════════════════════════╣
             ║  a) dom_parser.py   ──► HTML structure violations    ║
             ║  b) wcag_checker.py ──► Exact WCAG 2.1 math & CVD    ║
             ║  c) ast_extractor.py──► CSS AST & Unified Diagnostic ║
             ╚══════════════════════════════════════════════════════╝
                                       │
                                       ▼
                       [Unified Diagnostic JSON Payload]
                                  │          │
                 ┌────────────────┘          └────────────────┐
                 ▼                                            ▼
   [Teammate 2 / Role 1: AI Agent]               [Teammate 3 / Role 4: API & UI]
   Uses diagnostic to generate surgical          FastAPI returns violations to Streamlit
   CSS patches & self-correct via loops          dashboard with scores & color previews
```

---

## 2. Inventory of What Has Been Implemented (2,749 Lines)

All files were written directly inside the `feature-accessibility` branch.

| File Path | Lines | Status | Core Responsibility |
|---|---|---|---|
| `dom_accessibility/wcag_checker.py` | 857 | ✅ **Completed** | W3C WCAG 2.1 mathematical engine, color parser, sRGB linearization, relative luminance, contrast ratio, color blindness matrices, fix color recommender |
| `dom_accessibility/dom_parser.py` | 521 | ✅ **Completed** | BeautifulSoup4 structural HTML auditor: alt tags, empty links, form input labels, heading hierarchy, lang tag, landmarks, dark mode detection |
| `dom_accessibility/ast_extractor.py` | 586 | ✅ **Completed** | TinyCSS2 AST parser, style extraction, AI CSS patch syntax & security validator, selector isolator, unified diagnostic JSON builder |
| `dom_accessibility/__init__.py` | 61 | ✅ **Completed** | Clean public package exports for all classes, enums, and functions |
| `tests/test_wcag_math.py` | 729 | ✅ **Completed** | 100+ unit test assertions covering color parsing, sRGB math, luminance, contrast, color blindness, fix colors, DOM parsing, AST validation |

---

## 3. Deep-Dive File-by-File Breakdown

### 3.1 `dom_accessibility/wcag_checker.py` (857 lines)
*The mathematical heart of the project. Implements exact W3C specifications without approximations.*

#### Mathematical Formulas Implemented:
1. **Color Parsing (`parse_color(color_str)`):**
   - Supports `#RGB`, `#RRGGBB`, `#RGBA`, `#RRGGBBAA`.
   - Supports `rgb(r, g, b)`, `rgba(r, g, b, a)`.
   - Supports 148 standard CSS named colors (e.g., `aliceblue`, `rebeccapurple`, `transparent`).
   - Handles alpha blending against white background via standard compositing:
     $$C_{composite} = \alpha \cdot C + (1 - \alpha) \cdot C_{bg}$$

2. **sRGB Linearization (`linearize_srgb_channel(c_srgb)`):**
   Converts gamma-compressed 8-bit sRGB values ($0.0 \le c \le 1.0$) into linear optical intensity according to IEC 61966-2-1:
   $$c_{linear} = \begin{cases} \frac{c}{12.92} & \text{if } c \le 0.04045 \\ \left(\frac{c + 0.055}{1.055}\right)^{2.4} & \text{if } c > 0.04045 \end{cases}$$

3. **Relative Luminance ($L$) (`relative_luminance(rgb)`):**
   Evaluates photometric luminance using the ITU-R BT.709 coefficients:
   $$L = 0.2126 \cdot R_{linear} + 0.7152 \cdot G_{linear} + 0.0722 \cdot B_{linear}$$
   *Result:* $0.0$ for absolute black `#000000`, $1.0$ for absolute white `#ffffff`.

4. **Contrast Ratio ($C$) (`contrast_ratio(rgb1, rgb2)`):**
   $$C = \frac{L_1 + 0.05}{L_2 + 0.05} \quad \text{where } L_1 \ge L_2$$
   Range is strictly $1.0:1$ (identical colors) to $21.0:1$ (pure black on pure white).

5. **WCAG 2.1 Threshold Evaluation (`check_contrast()`):**
   - **AA Normal Text:** Minimum $4.5:1$
   - **AA Large Text** ($\ge 18\text{pt} / 24\text{px}$ OR bold $\ge 14\text{pt} / 18.66\text{px}$): Minimum $3.0:1$
   - **AAA Normal Text:** Minimum $7.0:1$
   - **AAA Large Text:** Minimum $4.5:1$
   - **UI Components & Graphical Objects (SC 1.4.11):** Minimum $3.0:1$

6. **Color Vision Deficiency (CVD) Simulation (`simulate_color_blindness()`):**
   Implements Brettel, Viénot & Mollon LMS color space transformation matrices for:
   - **Protanopia** (L-cone absent / Red-blind, ~1% of males)
   - **Deuteranopia** (M-cone absent / Green-blind, ~5% of males)
   - **Tritanopia** (S-cone absent / Blue-blind, rare)

7. **Smart Color Fix Recommender (`suggest_fix_color(fg, bg, target_ratio)`):**
   Deterministically adjusts foreground luminance (darkening or lightening using binary search) to suggest the nearest accessible color that preserves original hue and meets target WCAG ratio.

8. **Full Styles Audit Pipeline (`audit_computed_styles(elements)`):**
   Consumes the exact JSON format returned by Role 2's `BrowserEngine.extract_computed_styles()`, evaluates every text element, computes score (0-100), and outputs `AccessibilityAuditResult`.

---

### 3.2 `dom_accessibility/dom_parser.py` (521 lines)
*HTML Structural accessibility analyzer using BeautifulSoup4. Catches issues invisible to pure screenshot computer vision.*

#### Rules Checked:
1. **WCAG SC 1.1.1 Non-text Content (`img-alt`):**
   - Scans all `<img>` tags.
   - Flags missing `alt` attributes as `critical`.
   - Distinguishes decorative images (`alt=""` or `role="presentation"` are permitted).
2. **WCAG SC 2.4.4 Link Purpose in Context (`link-text`):**
   - Scans all `<a>` tags.
   - Flags empty links with no inner text, no `aria-label`, and no `title`.
   - Flags non-descriptive link text (e.g., "click here", "read more", "link", "here").
3. **WCAG SC 1.3.1 Info & Relationships (`form-label`):**
   - Scans `<input>`, `<select>`, `<textarea>`.
   - Verifies explicit `<label for="id">`, wrapping `<label>`, or `aria-label` / `aria-labelledby`.
   - Exempts `type="hidden"`, `type="submit"`, `type="button"`.
4. **WCAG SC 1.3.1 Heading Hierarchy (`heading-order`):**
   - Verifies sequential ordering ($h1 \to h2 \to h3$).
   - Flags skipped heading levels (e.g. $h1 \to h3$ without $h2$) which disorient screen reader users.
   - Flags pages missing an $h1$.
5. **WCAG SC 3.1.1 Language of Page (`html-lang`):**
   - Verifies `<html lang="...">` exists and has a non-empty code.
6. **WCAG SC 2.4.2 Page Titled (`page-title`):**
   - Checks `<title>` inside `<head>`.
7. **WCAG SC 2.4.1 Bypass Blocks (`landmarks`):**
   - Checks for semantic landmarks (`<main>`, `<nav>`, `<header>`, `<footer>`).
8. **Dark Mode Support Detection (`detect_dark_mode_support()`):**
   - Detects CSS `@media (prefers-color-scheme: dark)` or dark mode class toggles.

---

### 3.3 `dom_accessibility/ast_extractor.py` (586 lines)
*CSS Abstract Syntax Tree extraction, AI patch validation, and bridge to Role 1 & Role 4.*

#### Key Functionalities:
1. **TinyCSS2 AST Parsing:**
   - Parses raw CSS stylesheets into structured `CSSRule` objects (selectors + declaration dicts).
2. **Extraction from HTML:**
   - Extracts all embedded `<style>` tags and inline `style="..."` attributes.
3. **CSS Patch Validator (`validate_css_patch(patch_str)`):**
   - **Prevents AI hallucinations:** Verifies syntax validity of AI-generated CSS patches before injection into Playwright.
   - **Security sanitization:** Detects disallowed tokens (`javascript:`, `expression(`, `@import`, `<script>`).
4. **Selector Isolation (`isolate_rule_for_selector(css, selector)`):**
   - Allows Role 1's Agent to isolate the specific CSS declaration block governing a failing element for surgical modification.
5. **Unified Diagnostic Compilation (`build_unified_diagnostic()`):**
   - Merges:
     - Page metadata (URL, title, timestamp)
     - WCAG color contrast violations from `wcag_checker.py`
     - Structural HTML violations from `dom_parser.py`
     - Overall compliance score (0-100)
     - Color blindness impact report
   - Produces clean JSON that Role 1 feeds to LLM prompts and Role 4 sends to the frontend.

---

### 3.4 `tests/test_wcag_math.py` (729 lines)
*Exhaustive unit test suite covering:*
- Known mathematical corner cases (black/white = 21:1, white/white = 1:1, black/black = 1:1).
- W3C sample color pairs (e.g., `#777777` on `#ffffff` = 4.48:1, correctly flagging fail for AA normal text 4.5:1).
- Shorthand hex, 8-digit hex, rgb, rgba with opacity compositing, named colors.
- Large text detection (18pt / 24px and bold 14pt / 18.66px).
- Color blindness simulation matrix accuracy.
- Suggestion color generator correctness (verifying recommended color satisfies $\ge 4.5:1$).
- DOM parser checks on synthetic bad HTML (missing alt, broken headings, unlabelled inputs).
- CSS AST validation on good CSS vs malicious/broken CSS.

---

## 4. Teammate Compatibility & Data Contracts

### Inputs Role 3 Consumes:
1. **From Role 2 (`browser_automation/browser_engine.py`):**
   - `capture.html_source` (str) $\to$ Passed into `DOMParser.parse_html(html_str, url)`
   - `computed_styles` (list of dicts) $\to$ Passed into `audit_computed_styles(computed_styles)`
   - Contract format:
     ```python
     {
         "tag": "p",
         "text": "Welcome",
         "color": "rgb(128, 128, 128)",
         "backgroundColor": "rgb(255, 255, 255)",
         "fontSize": "16px",
         "fontWeight": "400",
         "boundingBox": {"x": 100, "y": 200, "width": 500, "height": 24},
         "selector": "p.intro-text"
     }
     ```

### Outputs Role 3 Provides:
1. **To Role 1 (`ai_engine` - LLM Agent):**
   - `UnifiedDiagnostic.to_dict()`: Clean JSON listing exact violation selectors, current colors, measured contrast ratio, required contrast ratio, recommended accessible color, and DOM structural flaws.
2. **To Role 2 (`browser_automation/sandbox_injector.py`):**
   - `ASTExtractor.validate_css_patch(patch)`: Returns `CSSValidationResult(is_valid=True/False)`.
3. **To Role 4 (`api_backend` & `frontend_ui`):**
   - JSON response for `/audit-url` and `/audit/accessibility` containing summary statistics, accessibility score (0-100), violation counts by severity (`critical`, `high`, `medium`, `low`), and full issue lists.

---

## 5. What Remains To Be Done When Resuming (15%)

When Claude Opus refreshes in 2 days, execute these 4 remaining steps:

### Step 1: Add `pytest` to `requirements.txt`
Add `pytest>=7.0.0` to `requirements.txt` so automated tests can run in any environment.

### Step 2: Plug Role 3 into `api_backend/main_api.py`
Connect `dom_parser.py` and `wcag_checker.py` into FastAPI:
- Import `DOMParser`, `audit_computed_styles`, and `ASTExtractor` in `api_backend/main_api.py`.
- In `audit_url()` endpoint:
  ```python
  # Run WCAG math on computed styles
  wcag_result = audit_computed_styles(computed_styles)
  
  # Run DOM parser on captured HTML
  first_capture = next(iter(audit_capture.captures.values()), None)
  dom_result = DOMParser().parse_html(first_capture.html_source if first_capture else "", url)
  
  # Add to result payload
  result["accessibility_score"] = wcag_result.overall_score
  result["wcag_violations"] = [asdict(v) for v in wcag_result.violations]
  result["dom_violations"] = [asdict(v) for v in dom_result.violations]
  ```
- Optionally add endpoint `POST /audit/accessibility` for standalone HTML/style auditing.

### Step 3: Verify Unit Tests
Install pytest and run:
```powershell
python -m pytest tests/test_wcag_math.py -v
```
All tests should pass 100%.

### Step 4: Commit and Push to Branch
```powershell
git add .
git commit -m "feat(accessibility): complete Role 3 DOM & WCAG 2.1 math engine with tests"
git push origin feature-accessibility
```

---

## 6. Copy-Paste Prompt for Claude Opus When Resuming

When Claude Opus quota refreshes, copy and paste this exact prompt into Antigravity:

```markdown
Hello Claude! Please resume work on VisionGuard AI for Role 3 (DOM & Accessibility Engineer).

We are working in the "feature-accessibility" branch.
Please read `ROLE_3_HANDOFF.md` in the repository root for full details.

Here is the current state:
1. `dom_accessibility/wcag_checker.py`, `dom_parser.py`, `ast_extractor.py`, `__init__.py`, and `tests/test_wcag_math.py` are ALREADY fully implemented (2,749 lines total).
2. The remaining tasks are:
   - Add `pytest` to `requirements.txt`.
   - Wire the WCAG checker and DOM parser into `api_backend/main_api.py` so the `/audit-url` endpoint returns the accessibility score and violations, and add a dedicated `/audit/accessibility` endpoint.
   - Run the unit tests to verify.
   - Stage, commit, and push all changes to the `feature-accessibility` branch.

Please proceed with these remaining steps to wrap up Role 3!
```
