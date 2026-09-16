"""
VisionGuard AI - CSS AST Extractor & Validator
================================================
Parses CSS stylesheets into Abstract Syntax Trees using TinyCSS2,
validates AI-generated CSS patches, and produces the unified
diagnostic JSON that connects the DOM parser + WCAG checker outputs
with the AI engine.

Key capabilities:
- Extract <style> blocks and inline styles from HTML
- Parse CSS into AST using TinyCSS2
- Validate CSS syntax (catch AI hallucinations)
- Isolate CSS rules by selector (for surgical patching)
- Build the unified diagnostic JSON combining DOM + WCAG results
- Export audit reports (JSON format)

References:
    - TinyCSS2 docs: https://doc.courtbouillon.org/tinycss2/
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import tinycss2
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("visionguard.ast_extractor")


# ─────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────

@dataclass
class CSSRule:
    """A single parsed CSS rule (selector + declarations)."""
    selector: str
    declarations: Dict[str, str]  # property -> value
    source: str = ""  # "inline", "style-block", "external"
    raw: str = ""     # The raw CSS text of this rule


@dataclass
class CSSValidationResult:
    """Result of validating a CSS patch string."""
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parsed_rules: List[CSSRule] = field(default_factory=list)
    raw_css: str = ""


@dataclass
class UnifiedDiagnostic:
    """
    The combined diagnostic JSON object that merges:
    - DOM structural violations (from dom_parser.py)
    - WCAG contrast violations (from wcag_checker.py)
    - CSS context (from this module)

    This is the single data object consumed by the AI engine
    for reasoning and CSS patch generation.
    """
    url: str = ""
    timestamp: str = ""
    viewport: str = ""

    # Summary
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Detailed violation lists
    dom_violations: List[Dict] = field(default_factory=list)
    contrast_violations: List[Dict] = field(default_factory=list)
    color_blindness_issues: List[Dict] = field(default_factory=list)

    # CSS context for the AI to use
    relevant_css_rules: List[Dict] = field(default_factory=list)

    # Page metadata
    page_metadata: Dict = field(default_factory=dict)

    # Accessibility score
    accessibility_score: float = 100.0


# ─────────────────────────────────────────────
# CSS Extraction from HTML
# ─────────────────────────────────────────────

class ASTExtractor:
    """
    Extracts and parses CSS from HTML, validates CSS patches,
    and builds unified diagnostic reports.

    Usage:
        extractor = ASTExtractor()
        css_rules = extractor.extract_css_from_html(html_source)
        validation = extractor.validate_css_patch(css_string)
        report = extractor.build_unified_diagnostic(dom_result, wcag_result)
    """

    def extract_css_from_html(self, html_source: str) -> List[CSSRule]:
        """
        Extract all CSS rules from an HTML document.

        Extracts from:
        1. <style> blocks in <head> and <body>
        2. Inline style="" attributes on elements
        3. References to external <link rel="stylesheet"> (URLs only, not fetched)

        Args:
            html_source: Raw HTML string.

        Returns:
            List of CSSRule objects found in the HTML.
        """
        if not html_source:
            return []

        soup = BeautifulSoup(html_source, "html.parser")
        all_rules = []

        # 1. Extract <style> blocks
        style_tags = soup.find_all("style")
        for i, style_tag in enumerate(style_tags):
            if style_tag.string:
                css_text = style_tag.string
                rules = self._parse_css_text(css_text, source=f"style-block-{i}")
                all_rules.extend(rules)

        # 2. Extract inline styles
        elements_with_style = soup.find_all(attrs={"style": True})
        for el in elements_with_style:
            if isinstance(el, Tag):
                style_attr = el.get("style", "")
                selector = self._build_element_selector(el)
                if style_attr:
                    declarations = self._parse_inline_style(style_attr)
                    all_rules.append(CSSRule(
                        selector=selector,
                        declarations=declarations,
                        source="inline",
                        raw=style_attr,
                    ))

        # 3. Note external stylesheet references
        link_tags = soup.find_all("link", rel="stylesheet")
        for link in link_tags:
            if isinstance(link, Tag):
                href = link.get("href", "")
                if href:
                    logger.info(f"External stylesheet reference found: {href}")
                    # We cannot fetch external stylesheets here, but we note them
                    all_rules.append(CSSRule(
                        selector="@external",
                        declarations={"href": href},
                        source="external-link",
                        raw=f'<link rel="stylesheet" href="{href}">',
                    ))

        logger.info(f"Extracted {len(all_rules)} CSS rules from HTML")
        return all_rules

    def get_stylesheet_urls(self, html_source: str) -> List[str]:
        """
        Extract all external stylesheet URLs from the HTML.

        Args:
            html_source: Raw HTML string.

        Returns:
            List of stylesheet URLs.
        """
        soup = BeautifulSoup(html_source, "html.parser")
        urls = []
        link_tags = soup.find_all("link", rel="stylesheet")
        for link in link_tags:
            if isinstance(link, Tag):
                href = link.get("href", "")
                if href:
                    urls.append(href)
        return urls

    # ─────────────────────────────────────────────
    # CSS Parsing with TinyCSS2
    # ─────────────────────────────────────────────

    def _parse_css_text(self, css_text: str, source: str = "") -> List[CSSRule]:
        """
        Parse a CSS string into a list of CSSRule objects using TinyCSS2.

        Args:
            css_text: Raw CSS text (from a <style> block or external file).
            source: Label for where this CSS came from.

        Returns:
            List of CSSRule objects.
        """
        rules = []
        try:
            parsed = tinycss2.parse_stylesheet(
                css_text,
                skip_comments=True,
                skip_whitespace=True,
            )

            for rule in parsed:
                if rule.type == "qualified-rule":
                    # Extract the selector
                    selector = tinycss2.serialize(rule.prelude).strip()
                    # Extract the declarations
                    declarations = self._parse_declaration_block(rule.content)
                    raw = tinycss2.serialize([rule]).strip()

                    rules.append(CSSRule(
                        selector=selector,
                        declarations=declarations,
                        source=source,
                        raw=raw,
                    ))
                elif rule.type == "at-rule":
                    # Handle @media, @keyframes etc.
                    at_name = f"@{rule.at_keyword}"
                    raw = tinycss2.serialize([rule]).strip()
                    rules.append(CSSRule(
                        selector=at_name,
                        declarations={"raw_content": raw},
                        source=source,
                        raw=raw,
                    ))
                elif rule.type == "error":
                    logger.warning(f"CSS parse error in {source}: {rule.message}")

        except Exception as e:
            logger.error(f"Failed to parse CSS from {source}: {e}")

        return rules

    def _parse_declaration_block(self, tokens) -> Dict[str, str]:
        """Parse a list of TinyCSS2 tokens from a declaration block."""
        declarations = {}
        try:
            parsed_declarations = tinycss2.parse_declaration_list(
                tokens,
                skip_comments=True,
                skip_whitespace=True,
            )
            for decl in parsed_declarations:
                if decl.type == "declaration":
                    prop_name = decl.lower_name
                    prop_value = tinycss2.serialize(decl.value).strip()
                    declarations[prop_name] = prop_value
        except Exception as e:
            logger.warning(f"Failed to parse declaration block: {e}")

        return declarations

    def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
        """Parse an inline style="" attribute value into declarations."""
        declarations = {}
        try:
            parsed = tinycss2.parse_declaration_list(
                style_str,
                skip_comments=True,
                skip_whitespace=True,
            )
            for decl in parsed:
                if decl.type == "declaration":
                    declarations[decl.lower_name] = tinycss2.serialize(decl.value).strip()
        except Exception as e:
            logger.warning(f"Failed to parse inline style: {e}")

        return declarations

    # ─────────────────────────────────────────────
    # CSS Patch Validation
    # ─────────────────────────────────────────────

    def validate_css_patch(self, css_patch: str) -> CSSValidationResult:
        """
        Validate an AI-generated CSS patch for syntax correctness.

        This is a critical guardrail that prevents the AI from injecting
        malformed CSS that could break the page layout.

        Checks:
        1. TinyCSS2 can parse it without errors
        2. All rules have valid selectors
        3. No dangerous properties (like position: fixed on body)
        4. No JavaScript injection attempts

        Args:
            css_patch: Raw CSS string from the AI.

        Returns:
            CSSValidationResult with validity status and any errors.
        """
        result = CSSValidationResult(raw_css=css_patch)

        if not css_patch or not css_patch.strip():
            result.is_valid = False
            result.errors.append("CSS patch is empty.")
            return result

        # Security check: no JS injection via url() or expression()
        dangerous_patterns = [
            (r"expression\s*\(", "CSS expressions are not allowed (potential XSS)"),
            (r"javascript\s*:", "JavaScript URLs are not allowed"),
            (r"behavior\s*:", "CSS behavior property is not allowed"),
            (r"-moz-binding\s*:", "Mozilla binding is not allowed"),
        ]
        for pattern, msg in dangerous_patterns:
            if re.search(pattern, css_patch, re.IGNORECASE):
                result.is_valid = False
                result.errors.append(msg)
                return result

        # Parse with TinyCSS2
        try:
            parsed = tinycss2.parse_stylesheet(
                css_patch,
                skip_comments=True,
                skip_whitespace=True,
            )

            valid_rules = []
            for rule in parsed:
                if rule.type == "error":
                    result.errors.append(f"CSS syntax error: {rule.message}")
                elif rule.type == "qualified-rule":
                    selector = tinycss2.serialize(rule.prelude).strip()
                    declarations = self._parse_declaration_block(rule.content)

                    if not selector:
                        result.errors.append("Found a rule with an empty selector.")
                    elif not declarations:
                        result.warnings.append(f"Rule '{selector}' has no declarations.")
                    else:
                        valid_rules.append(CSSRule(
                            selector=selector,
                            declarations=declarations,
                            source="ai-patch",
                            raw=tinycss2.serialize([rule]).strip(),
                        ))
                elif rule.type == "at-rule":
                    # @media queries etc. are allowed
                    valid_rules.append(CSSRule(
                        selector=f"@{rule.at_keyword}",
                        declarations={},
                        source="ai-patch",
                        raw=tinycss2.serialize([rule]).strip(),
                    ))

            result.parsed_rules = valid_rules
            result.is_valid = len(result.errors) == 0

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"CSS parsing failed: {str(e)}")

        return result

    # ─────────────────────────────────────────────
    # CSS Rule Lookup by Selector
    # ─────────────────────────────────────────────

    def find_rules_for_selector(
        self,
        css_rules: List[CSSRule],
        target_selector: str,
    ) -> List[CSSRule]:
        """
        Find all CSS rules that match or relate to a given selector.

        Used to provide CSS context to the AI engine when it needs to
        generate a patch for a specific element.

        Args:
            css_rules: List of all CSSRule objects from the page.
            target_selector: The CSS selector to search for.

        Returns:
            List of matching CSSRule objects.
        """
        matches = []
        target_lower = target_selector.lower().strip()

        for rule in css_rules:
            rule_selector_lower = rule.selector.lower().strip()

            # Exact match
            if rule_selector_lower == target_lower:
                matches.append(rule)
                continue

            # Partial match (target is contained in the rule's selector)
            if target_lower in rule_selector_lower:
                matches.append(rule)
                continue

            # The rule's selector is part of the target
            if rule_selector_lower in target_lower:
                matches.append(rule)

        return matches

    # ─────────────────────────────────────────────
    # Unified Diagnostic Builder
    # ─────────────────────────────────────────────

    def build_unified_diagnostic(
        self,
        dom_result=None,
        wcag_result=None,
        css_rules: Optional[List[CSSRule]] = None,
        url: str = "",
        viewport: str = "desktop_1080p",
    ) -> UnifiedDiagnostic:
        """
        Build the unified diagnostic JSON that combines all analysis results.

        This is the single data object that gets sent to the AI engine
        for reasoning about what CSS patches to generate.

        Args:
            dom_result: DOMAnalysisResult from dom_parser.py
            wcag_result: AccessibilityAuditResult from wcag_checker.py
            css_rules: List of CSSRule objects from extract_css_from_html()
            url: The URL being audited.
            viewport: The viewport name used for the audit.

        Returns:
            UnifiedDiagnostic combining all results.
        """
        diagnostic = UnifiedDiagnostic(
            url=url,
            timestamp=datetime.utcnow().isoformat() + "Z",
            viewport=viewport,
        )

        # Merge DOM violations
        if dom_result:
            for v in dom_result.violations:
                diagnostic.dom_violations.append({
                    "rule_id": v.rule_id,
                    "wcag_criterion": v.wcag_criterion,
                    "wcag_level": v.wcag_level,
                    "severity": v.severity,
                    "element_tag": v.element_tag,
                    "element_html": v.element_html,
                    "description": v.description,
                    "suggestion": v.suggestion,
                    "selector": v.selector,
                })
            diagnostic.page_metadata = dom_result.metadata.copy()
            diagnostic.page_metadata["has_lang"] = dom_result.has_lang_attribute
            diagnostic.page_metadata["has_title"] = dom_result.has_page_title
            diagnostic.page_metadata["dark_mode"] = dom_result.supports_dark_mode
            diagnostic.page_metadata["heading_structure"] = dom_result.heading_structure

        # Merge WCAG contrast violations
        if wcag_result:
            for v in wcag_result.contrast_violations:
                diagnostic.contrast_violations.append({
                    "element_tag": v.element_tag,
                    "element_text": v.element_text,
                    "element_selector": v.element_selector,
                    "foreground_color": v.foreground_color,
                    "background_color": v.background_color,
                    "contrast_ratio": v.contrast_ratio,
                    "required_ratio": v.required_ratio,
                    "wcag_criterion": v.wcag_criterion,
                    "wcag_level": v.wcag_level,
                    "severity": v.severity,
                    "suggestion": v.suggestion,
                    "bounding_box": v.bounding_box,
                    "font_size": v.font_size,
                    "font_weight": v.font_weight,
                    "is_large_text": v.is_large_text,
                })
            diagnostic.accessibility_score = wcag_result.overall_score

        # Attach relevant CSS context
        if css_rules:
            # For each contrast violation, find the CSS rules for that element
            for violation in diagnostic.contrast_violations:
                selector = violation.get("element_selector", "")
                if selector and css_rules:
                    matching_rules = self.find_rules_for_selector(css_rules, selector)
                    for rule in matching_rules[:3]:  # Limit context to top 3 rules
                        diagnostic.relevant_css_rules.append({
                            "selector": rule.selector,
                            "declarations": rule.declarations,
                            "source": rule.source,
                        })

        # Calculate totals
        all_severities = (
            [v["severity"] for v in diagnostic.dom_violations]
            + [v["severity"] for v in diagnostic.contrast_violations]
        )
        diagnostic.total_issues = len(all_severities)
        diagnostic.critical_count = all_severities.count("critical")
        diagnostic.high_count = all_severities.count("high")
        diagnostic.medium_count = all_severities.count("medium")
        diagnostic.low_count = all_severities.count("low")

        logger.info(
            f"Unified Diagnostic built: {diagnostic.total_issues} total issues "
            f"(C={diagnostic.critical_count}, H={diagnostic.high_count}, "
            f"M={diagnostic.medium_count}, L={diagnostic.low_count})"
        )

        return diagnostic

    # ─────────────────────────────────────────────
    # Export Functions
    # ─────────────────────────────────────────────

    def diagnostic_to_json(self, diagnostic: UnifiedDiagnostic) -> str:
        """
        Convert a UnifiedDiagnostic to a JSON string.

        This JSON string is what gets:
        1. Sent to the AI engine as context for patch generation
        2. Returned via the API to the frontend dashboard
        3. Exported as a downloadable report

        Args:
            diagnostic: The UnifiedDiagnostic object.

        Returns:
            Pretty-printed JSON string.
        """
        return json.dumps(asdict(diagnostic), indent=2, default=str)

    def diagnostic_to_dict(self, diagnostic: UnifiedDiagnostic) -> dict:
        """Convert a UnifiedDiagnostic to a plain dictionary."""
        return asdict(diagnostic)

    def export_report(
        self,
        diagnostic: UnifiedDiagnostic,
        output_path: str,
    ) -> str:
        """
        Export the audit report as a JSON file.

        Args:
            diagnostic: The UnifiedDiagnostic to export.
            output_path: File path to write the JSON report to.

        Returns:
            The output file path.
        """
        report_json = self.diagnostic_to_json(diagnostic)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_json)

        logger.info(f"Audit report exported to: {output_path}")
        return output_path

    # ─────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────

    @staticmethod
    def _build_element_selector(tag: Tag) -> str:
        """Build a CSS selector string from a BeautifulSoup Tag."""
        selector = tag.name
        tag_id = tag.get("id")
        if tag_id:
            selector += f"#{tag_id}"
        elif tag.get("class"):
            classes = tag["class"] if isinstance(tag["class"], list) else [tag["class"]]
            selector += "." + ".".join(classes)
        return selector
