"""
VisionGuard AI - DOM Parser
=============================
Parses raw HTML using BeautifulSoup4 to extract accessibility-relevant
elements and detect structural WCAG violations that cannot be found
through visual inspection alone.

This module checks the HTML structure for:
- Missing alt attributes on images
- Missing aria-label / link text on interactive elements
- Form inputs without associated labels
- Heading hierarchy violations (skipped levels)
- Missing lang attribute on <html>
- Missing page title
- Insufficient landmark / semantic elements
- prefers-color-scheme dark mode support detection

These are DOM-level (structural) checks that complement the visual/color
checks performed by wcag_checker.py.

References:
    - WCAG 2.1 SC 1.1.1 Non-text Content
    - WCAG 2.1 SC 1.3.1 Info and Relationships
    - WCAG 2.1 SC 2.4.1 Bypass Blocks
    - WCAG 2.1 SC 2.4.2 Page Titled
    - WCAG 2.1 SC 3.1.1 Language of Page
    - WCAG 2.1 SC 4.1.2 Name, Role, Value
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("visionguard.dom_parser")


# ─────────────────────────────────────────────
# Data Classes for Structured Output
# ─────────────────────────────────────────────

@dataclass
class DOMViolation:
    """A single DOM-level accessibility violation."""
    rule_id: str            # e.g. "img-alt", "link-text", "heading-order"
    wcag_criterion: str     # e.g. "1.1.1 Non-text Content"
    wcag_level: str         # "A", "AA", or "AAA"
    severity: str           # "critical", "high", "medium", "low"
    element_tag: str        # e.g. "img", "a", "input"
    element_html: str       # Short snippet of the offending element
    description: str        # Human-readable explanation
    suggestion: str         # How to fix it
    selector: str = ""      # CSS selector to locate the element


@dataclass
class DOMAnalysisResult:
    """Complete output of a DOM structural accessibility audit."""
    url: str = ""
    total_violations: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    violations: List[DOMViolation] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    # Summary counters
    total_images: int = 0
    images_missing_alt: int = 0
    total_links: int = 0
    links_missing_text: int = 0
    total_form_inputs: int = 0
    inputs_missing_labels: int = 0
    has_lang_attribute: bool = False
    has_page_title: bool = False
    heading_structure: List[str] = field(default_factory=list)
    supports_dark_mode: bool = False


# ─────────────────────────────────────────────
# DOM Parser Class
# ─────────────────────────────────────────────

class DOMParser:
    """
    Parses raw HTML and checks for structural accessibility violations.

    Usage:
        parser = DOMParser()
        result = parser.analyze(html_source, url="https://example.com")
    """

    def analyze(self, html_source: str, url: str = "") -> DOMAnalysisResult:
        """
        Run a complete DOM accessibility analysis on raw HTML.

        Args:
            html_source: The full HTML source string (from PageCapture.html_source).
            url: The URL being audited (for reporting).

        Returns:
            DOMAnalysisResult containing all structural violations found.
        """
        result = DOMAnalysisResult(url=url)

        if not html_source or not html_source.strip():
            logger.warning("Empty HTML source provided to DOMParser")
            return result

        soup = BeautifulSoup(html_source, "html.parser")

        # Run all structural checks
        self._check_lang_attribute(soup, result)
        self._check_page_title(soup, result)
        self._check_images_alt(soup, result)
        self._check_links(soup, result)
        self._check_form_inputs(soup, result)
        self._check_heading_hierarchy(soup, result)
        self._check_landmarks(soup, result)
        self._check_dark_mode_support(html_source, result)
        self._check_meta_viewport(soup, result)
        self._check_tabindex(soup, result)
        self._check_autoplaying_media(soup, result)

        # Calculate totals
        result.total_violations = len(result.violations)
        result.critical_count = sum(1 for v in result.violations if v.severity == "critical")
        result.high_count = sum(1 for v in result.violations if v.severity == "high")
        result.medium_count = sum(1 for v in result.violations if v.severity == "medium")
        result.low_count = sum(1 for v in result.violations if v.severity == "low")

        logger.info(
            f"DOM Analysis: {result.total_violations} violations found "
            f"(C={result.critical_count}, H={result.high_count}, "
            f"M={result.medium_count}, L={result.low_count})"
        )

        return result

    # ── Individual Check Methods ──────────────────────────────

    def _check_lang_attribute(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 3.1.1: Check that <html> has a lang attribute."""
        html_tag = soup.find("html")
        if html_tag and isinstance(html_tag, Tag):
            lang = html_tag.get("lang", "")
            result.has_lang_attribute = bool(lang)
            if not lang:
                result.violations.append(DOMViolation(
                    rule_id="html-has-lang",
                    wcag_criterion="3.1.1 Language of Page",
                    wcag_level="A",
                    severity="high",
                    element_tag="html",
                    element_html="<html>",
                    description=(
                        "The <html> element does not have a 'lang' attribute. "
                        "Screen readers need this to determine the correct pronunciation."
                    ),
                    suggestion="Add lang='en' (or the appropriate language code) to the <html> tag.",
                ))
        else:
            result.has_lang_attribute = False

    def _check_page_title(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 2.4.2: Check that the page has a <title>."""
        title_tag = soup.find("title")
        if title_tag and title_tag.string and title_tag.string.strip():
            result.has_page_title = True
            result.metadata["page_title"] = title_tag.string.strip()
        else:
            result.has_page_title = False
            result.violations.append(DOMViolation(
                rule_id="page-has-title",
                wcag_criterion="2.4.2 Page Titled",
                wcag_level="A",
                severity="high",
                element_tag="head",
                element_html="<title></title>",
                description="The page does not have a meaningful <title> element.",
                suggestion="Add a descriptive <title> tag inside <head>.",
            ))

    def _check_images_alt(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 1.1.1: Check all <img> tags have alt attributes."""
        images = soup.find_all("img")
        result.total_images = len(images)

        for img in images:
            if not isinstance(img, Tag):
                continue

            alt = img.get("alt")
            src = img.get("src", "unknown")
            selector = self._build_selector(img)

            if alt is None:
                # Missing alt attribute entirely — critical
                result.images_missing_alt += 1
                result.violations.append(DOMViolation(
                    rule_id="img-alt",
                    wcag_criterion="1.1.1 Non-text Content",
                    wcag_level="A",
                    severity="critical",
                    element_tag="img",
                    element_html=str(img)[:150],
                    description=(
                        f"Image is missing the 'alt' attribute entirely. "
                        f"Screen readers cannot describe this image. (src: {src[:80]})"
                    ),
                    suggestion=(
                        "Add alt='description' to the <img> tag. "
                        "If the image is decorative, use alt='' (empty string)."
                    ),
                    selector=selector,
                ))
            # Note: alt="" (empty string) is valid for decorative images

    def _check_links(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 2.4.4 & 4.1.2: Check links have discernible text."""
        links = soup.find_all("a")
        result.total_links = len(links)

        for link in links:
            if not isinstance(link, Tag):
                continue

            link_text = link.get_text(strip=True)
            aria_label = link.get("aria-label", "")
            aria_labelledby = link.get("aria-labelledby", "")
            title = link.get("title", "")
            href = link.get("href", "")

            # Check if any accessible name exists
            has_name = bool(link_text or aria_label or aria_labelledby or title)

            # Also check for image links with alt text
            if not has_name:
                inner_img = link.find("img")
                if inner_img and isinstance(inner_img, Tag) and inner_img.get("alt"):
                    has_name = True

            if not has_name and href:
                result.links_missing_text += 1
                result.violations.append(DOMViolation(
                    rule_id="link-name",
                    wcag_criterion="2.4.4 Link Purpose / 4.1.2 Name, Role, Value",
                    wcag_level="A",
                    severity="critical",
                    element_tag="a",
                    element_html=str(link)[:150],
                    description=(
                        f"Link has no discernible text. Screen readers will read "
                        f"the URL instead, which is not meaningful. (href: {href[:80]})"
                    ),
                    suggestion=(
                        "Add visible text inside the <a> tag, or add an "
                        "aria-label='description' attribute."
                    ),
                    selector=self._build_selector(link),
                ))

    def _check_form_inputs(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 1.3.1 & 4.1.2: Check form inputs have associated labels."""
        inputs = soup.find_all(["input", "select", "textarea"])
        result.total_form_inputs = len(inputs)

        for inp in inputs:
            if not isinstance(inp, Tag):
                continue

            # Skip hidden and submit/button types
            input_type = inp.get("type", "text").lower()
            if input_type in ("hidden", "submit", "button", "reset", "image"):
                continue

            input_id = inp.get("id", "")
            aria_label = inp.get("aria-label", "")
            aria_labelledby = inp.get("aria-labelledby", "")
            placeholder = inp.get("placeholder", "")
            title = inp.get("title", "")

            # Check for associated <label>
            has_label = bool(aria_label or aria_labelledby or title)

            if input_id and not has_label:
                # Look for a <label for="..."> that references this input
                label = soup.find("label", attrs={"for": input_id})
                if label:
                    has_label = True

            if not has_label:
                # Check if the input is wrapped inside a <label>
                parent_label = inp.find_parent("label")
                if parent_label:
                    has_label = True

            if not has_label:
                result.inputs_missing_labels += 1
                severity = "high" if not placeholder else "medium"
                result.violations.append(DOMViolation(
                    rule_id="input-label",
                    wcag_criterion="1.3.1 Info and Relationships / 4.1.2 Name, Role, Value",
                    wcag_level="A",
                    severity=severity,
                    element_tag=inp.name,
                    element_html=str(inp)[:150],
                    description=(
                        f"Form {inp.name} element has no associated label. "
                        f"Screen readers cannot identify the purpose of this input."
                    ),
                    suggestion=(
                        f"Add a <label for='{input_id or 'inputId'}'> element, "
                        f"or add an aria-label attribute to the {inp.name} element."
                    ),
                    selector=self._build_selector(inp),
                ))

    def _check_heading_hierarchy(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 1.3.1: Check heading levels don't skip (e.g., h1 → h3)."""
        headings = soup.find_all(re.compile(r"^h[1-6]$"))
        heading_levels = []

        for h in headings:
            if isinstance(h, Tag):
                level = int(h.name[1])
                heading_levels.append(level)
                result.heading_structure.append(f"h{level}: {h.get_text(strip=True)[:60]}")

        # Check for skipped levels
        for i in range(1, len(heading_levels)):
            current = heading_levels[i]
            previous = heading_levels[i - 1]

            if current > previous + 1:
                result.violations.append(DOMViolation(
                    rule_id="heading-order",
                    wcag_criterion="1.3.1 Info and Relationships",
                    wcag_level="A",
                    severity="medium",
                    element_tag=f"h{current}",
                    element_html=str(headings[i])[:150],
                    description=(
                        f"Heading level skipped: h{previous} is followed by h{current}. "
                        f"This breaks the document outline for screen reader users."
                    ),
                    suggestion=(
                        f"Use h{previous + 1} instead of h{current}, or add the "
                        f"missing intermediate heading levels."
                    ),
                    selector=self._build_selector(headings[i]),
                ))

        # Check: is there at least one h1?
        if heading_levels and 1 not in heading_levels:
            result.violations.append(DOMViolation(
                rule_id="page-has-h1",
                wcag_criterion="1.3.1 Info and Relationships",
                wcag_level="A",
                severity="medium",
                element_tag="body",
                element_html="<body>",
                description="The page does not have an <h1> heading.",
                suggestion="Add a single <h1> element as the primary page heading.",
            ))

    def _check_landmarks(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 1.3.1 / 2.4.1: Check for semantic landmark elements."""
        landmark_tags = ["main", "nav", "header", "footer", "aside"]
        landmark_roles = ["main", "navigation", "banner", "contentinfo", "complementary"]

        found_landmarks = []
        for tag in landmark_tags:
            if soup.find(tag):
                found_landmarks.append(tag)

        for role in landmark_roles:
            if soup.find(attrs={"role": role}):
                found_landmarks.append(f"role={role}")

        result.metadata["landmarks_found"] = found_landmarks

        # Check for missing <main> landmark
        has_main = bool(soup.find("main") or soup.find(attrs={"role": "main"}))
        if not has_main:
            result.violations.append(DOMViolation(
                rule_id="landmark-main",
                wcag_criterion="2.4.1 Bypass Blocks",
                wcag_level="A",
                severity="medium",
                element_tag="body",
                element_html="<body>",
                description=(
                    "The page does not have a <main> landmark element. "
                    "Landmark elements help screen reader users navigate the page structure."
                ),
                suggestion="Wrap the primary page content in a <main> element.",
            ))

    def _check_dark_mode_support(self, html_source: str, result: DOMAnalysisResult) -> None:
        """Detect if the page supports prefers-color-scheme for dark mode."""
        # Search for prefers-color-scheme in inline styles or the HTML
        if "prefers-color-scheme" in html_source:
            result.supports_dark_mode = True
            result.metadata["dark_mode"] = "supported"
        else:
            result.supports_dark_mode = False
            result.metadata["dark_mode"] = "not detected"

    def _check_meta_viewport(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 1.4.4: Check viewport meta doesn't disable zooming."""
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        if viewport_meta and isinstance(viewport_meta, Tag):
            content = viewport_meta.get("content", "")
            if isinstance(content, str):
                # Check for maximum-scale=1 or user-scalable=no
                if "user-scalable=no" in content.lower() or "user-scalable=0" in content.lower():
                    result.violations.append(DOMViolation(
                        rule_id="meta-viewport-scale",
                        wcag_criterion="1.4.4 Resize Text",
                        wcag_level="AA",
                        severity="high",
                        element_tag="meta",
                        element_html=str(viewport_meta)[:150],
                        description=(
                            "The viewport meta tag disables user scaling with "
                            "'user-scalable=no'. This prevents users with low "
                            "vision from zooming in."
                        ),
                        suggestion="Remove 'user-scalable=no' from the viewport meta tag.",
                    ))

                max_scale_match = re.search(r"maximum-scale\s*=\s*([\d.]+)", content.lower())
                if max_scale_match:
                    max_scale = float(max_scale_match.group(1))
                    if max_scale < 2.0:
                        result.violations.append(DOMViolation(
                            rule_id="meta-viewport-max-scale",
                            wcag_criterion="1.4.4 Resize Text",
                            wcag_level="AA",
                            severity="medium",
                            element_tag="meta",
                            element_html=str(viewport_meta)[:150],
                            description=(
                                f"The viewport meta tag restricts zoom to "
                                f"maximum-scale={max_scale}. Users should be "
                                f"able to zoom to at least 200%."
                            ),
                            suggestion="Set maximum-scale to at least 2.0 or remove it entirely.",
                        ))

    def _check_tabindex(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """Check for positive tabindex values that disrupt natural tab order."""
        elements_with_tabindex = soup.find_all(attrs={"tabindex": True})
        for el in elements_with_tabindex:
            if not isinstance(el, Tag):
                continue
            try:
                tabindex = int(el.get("tabindex", 0))
                if tabindex > 0:
                    result.violations.append(DOMViolation(
                        rule_id="tabindex-positive",
                        wcag_criterion="2.4.3 Focus Order",
                        wcag_level="A",
                        severity="medium",
                        element_tag=el.name,
                        element_html=str(el)[:150],
                        description=(
                            f"Element has tabindex={tabindex}. Positive tabindex values "
                            f"disrupt the natural tab order of the page."
                        ),
                        suggestion=(
                            "Use tabindex='0' to add to natural tab order, "
                            "or tabindex='-1' for programmatic focus only."
                        ),
                        selector=self._build_selector(el),
                    ))
            except (ValueError, TypeError):
                pass

    def _check_autoplaying_media(self, soup: BeautifulSoup, result: DOMAnalysisResult) -> None:
        """WCAG 1.4.2: Check for autoplaying audio/video."""
        media_elements = soup.find_all(["audio", "video"])
        for media in media_elements:
            if not isinstance(media, Tag):
                continue
            if media.has_attr("autoplay"):
                result.violations.append(DOMViolation(
                    rule_id="no-autoplay",
                    wcag_criterion="1.4.2 Audio Control",
                    wcag_level="A",
                    severity="high",
                    element_tag=media.name,
                    element_html=str(media)[:150],
                    description=(
                        f"A <{media.name}> element has the 'autoplay' attribute. "
                        f"Autoplaying media can be disorienting for screen reader users."
                    ),
                    suggestion=(
                        "Remove the 'autoplay' attribute or ensure the user can "
                        "easily pause or stop the media."
                    ),
                    selector=self._build_selector(media),
                ))

    # ── Utility ───────────────────────────────────────────────

    @staticmethod
    def _build_selector(tag: Tag) -> str:
        """Build a simple CSS selector string for a BeautifulSoup Tag."""
        selector = tag.name
        if tag.get("id"):
            selector += f"#{tag['id']}"
        elif tag.get("class"):
            classes = tag["class"] if isinstance(tag["class"], list) else [tag["class"]]
            selector += "." + ".".join(classes)
        return selector
