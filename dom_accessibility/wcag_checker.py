"""
VisionGuard AI - WCAG 2.1 Deterministic Math Engine
=====================================================
The "Symbolic" half of the Neuro-Symbolic architecture.

This module contains ZERO AI/LLM code. Every calculation is
hard-coded from the W3C WCAG 2.1 specification to guarantee
100% mathematical precision. The AI cannot hallucinate math
because this module does all the math deterministically.

Key capabilities:
- Parse CSS color strings (hex, rgb, rgba, named colors)
- WCAG 2.1 sRGB linearization
- Relative luminance calculation
- Contrast ratio calculation
- WCAG AA / AAA compliance evaluation
- Color blindness simulation (Protanopia, Deuteranopia, Tritanopia)
- Full accessibility audit on computed styles from BrowserEngine

References:
    - WCAG 2.1 Contrast: https://www.w3.org/TR/WCAG21/#contrast-minimum
    - Relative Luminance: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
"""

import logging
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("visionguard.wcag_checker")


# ─────────────────────────────────────────────
# Constants & Enums
# ─────────────────────────────────────────────

class WCAGLevel(str, Enum):
    """WCAG 2.1 conformance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class Severity(str, Enum):
    """Severity of an accessibility violation."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# WCAG 2.1 Contrast Ratio Thresholds
WCAG_THRESHOLDS = {
    "AA_normal":  4.5,   # Normal text (< 18pt or < 14pt bold)
    "AA_large":   3.0,   # Large text  (>= 18pt or >= 14pt bold)
    "AAA_normal": 7.0,   # Enhanced: normal text
    "AAA_large":  4.5,   # Enhanced: large text
}

# Large text breakpoints (in pixels, assuming 1pt ≈ 1.333px)
LARGE_TEXT_PX = 24.0        # 18pt * 1.333 ≈ 24px
LARGE_TEXT_BOLD_PX = 18.67  # 14pt * 1.333 ≈ 18.67px
BOLD_WEIGHT_THRESHOLD = 700  # CSS fontWeight >= 700 is "bold"

# W3C named CSS colors (subset of the 148 standard named colors)
NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "lime": (0, 255, 0),
    "aqua": (0, 255, 255),
    "teal": (0, 128, 128),
    "navy": (0, 0, 128),
    "fuchsia": (255, 0, 255),
    "purple": (128, 0, 128),
    "orange": (255, 165, 0),
    "pink": (255, 192, 203),
    "brown": (165, 42, 42),
    "coral": (255, 127, 80),
    "crimson": (220, 20, 60),
    "darkblue": (0, 0, 139),
    "darkgreen": (0, 100, 0),
    "darkred": (139, 0, 0),
    "darkgray": (169, 169, 169),
    "darkgrey": (169, 169, 169),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "gold": (255, 215, 0),
    "indigo": (75, 0, 130),
    "ivory": (255, 255, 240),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "lightblue": (173, 216, 230),
    "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211),
    "lightgreen": (144, 238, 144),
    "lightyellow": (255, 255, 224),
    "midnightblue": (25, 25, 112),
    "mintcream": (245, 255, 250),
    "mistyrose": (255, 228, 225),
    "moccasin": (255, 228, 181),
    "navajowhite": (255, 222, 173),
    "oldlace": (253, 245, 230),
    "orangered": (255, 69, 0),
    "orchid": (218, 112, 214),
    "peru": (205, 133, 63),
    "plum": (221, 160, 221),
    "royalblue": (65, 105, 225),
    "salmon": (250, 128, 114),
    "sienna": (160, 82, 45),
    "skyblue": (135, 206, 235),
    "slategray": (112, 128, 144),
    "slategrey": (112, 128, 144),
    "steelblue": (70, 130, 180),
    "tan": (210, 180, 140),
    "thistle": (216, 191, 216),
    "tomato": (255, 99, 71),
    "turquoise": (64, 224, 208),
    "violet": (238, 130, 238),
    "wheat": (245, 222, 179),
    "whitesmoke": (245, 245, 245),
    "yellowgreen": (154, 205, 50),
    "transparent": (0, 0, 0),  # Treated as black with zero alpha
}


# ─────────────────────────────────────────────
# Data Classes for Structured Output
# ─────────────────────────────────────────────

@dataclass
class ContrastResult:
    """Result of a single contrast ratio evaluation."""
    foreground_color: str
    background_color: str
    contrast_ratio: float
    passes_aa_normal: bool
    passes_aa_large: bool
    passes_aaa_normal: bool
    passes_aaa_large: bool
    is_large_text: bool
    passes_required: bool  # Based on whether it's large or normal text
    wcag_level_met: str    # "AAA", "AA", or "FAIL"


@dataclass
class ContrastViolation:
    """A single WCAG contrast violation detected on a page element."""
    element_tag: str
    element_text: str
    element_selector: str
    foreground_color: str
    background_color: str
    contrast_ratio: float
    required_ratio: float
    wcag_criterion: str     # e.g. "1.4.3 Contrast (Minimum)"
    wcag_level: str         # "AA" or "AAA"
    severity: str
    suggestion: str
    bounding_box: Optional[dict] = None
    font_size: str = ""
    font_weight: str = ""
    is_large_text: bool = False


@dataclass
class AccessibilityAuditResult:
    """Complete output of a WCAG accessibility audit on computed styles."""
    url: str = ""
    total_elements_checked: int = 0
    total_violations: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    contrast_violations: List[ContrastViolation] = field(default_factory=list)
    overall_score: float = 100.0  # Percentage of passing elements


# ─────────────────────────────────────────────
# Color Parsing
# ─────────────────────────────────────────────

def parse_color(color_str: str) -> Optional[Tuple[int, int, int, float]]:
    """
    Parse a CSS color string into an (R, G, B, A) tuple.

    Supports:
        - Hex: #RGB, #RRGGBB, #RRGGBBAA
        - RGB: rgb(r, g, b)
        - RGBA: rgba(r, g, b, a)
        - Named colors: "red", "white", "transparent", etc.

    Args:
        color_str: A CSS color value string.

    Returns:
        Tuple of (R, G, B, A) where R/G/B are 0-255 ints and A is 0.0-1.0 float.
        Returns None if the color cannot be parsed.
    """
    if not color_str or not isinstance(color_str, str):
        return None

    color_str = color_str.strip().lower()

    # Handle "transparent"
    if color_str == "transparent":
        return (0, 0, 0, 0.0)

    # Named colors
    if color_str in NAMED_COLORS:
        r, g, b = NAMED_COLORS[color_str]
        return (r, g, b, 1.0)

    # rgb(r, g, b) or rgb(r g b)
    rgb_match = re.match(
        r"rgb\(\s*(\d{1,3})\s*[,\s]\s*(\d{1,3})\s*[,\s]\s*(\d{1,3})\s*\)",
        color_str,
    )
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return (_clamp(r), _clamp(g), _clamp(b), 1.0)

    # rgba(r, g, b, a)
    rgba_match = re.match(
        r"rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([\d.]+)\s*\)",
        color_str,
    )
    if rgba_match:
        r = int(rgba_match.group(1))
        g = int(rgba_match.group(2))
        b = int(rgba_match.group(3))
        a = float(rgba_match.group(4))
        return (_clamp(r), _clamp(g), _clamp(b), max(0.0, min(1.0, a)))

    # Hex: #RGB, #RRGGBB, #RRGGBBAA
    hex_match = re.match(r"^#([0-9a-f]{3,8})$", color_str)
    if hex_match:
        hex_val = hex_match.group(1)
        if len(hex_val) == 3:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
            return (r, g, b, 1.0)
        elif len(hex_val) == 6:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            return (r, g, b, 1.0)
        elif len(hex_val) == 8:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            a = int(hex_val[6:8], 16) / 255.0
            return (r, g, b, a)

    logger.warning(f"Could not parse color: '{color_str}'")
    return None


def _clamp(value: int, min_val: int = 0, max_val: int = 255) -> int:
    """Clamp an integer to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


# ─────────────────────────────────────────────
# WCAG 2.1 Luminance & Contrast Math
# ─────────────────────────────────────────────

def linearize_srgb_channel(channel_8bit: int) -> float:
    """
    Linearize a single sRGB channel value per the WCAG 2.1 specification.

    The sRGB standard uses gamma compression. To calculate luminance,
    we must first undo this compression (linearize) using the exact
    piecewise formula from the W3C specification:

        If c_srgb <= 0.04045:
            c_linear = c_srgb / 12.92
        Else:
            c_linear = ((c_srgb + 0.055) / 1.055) ^ 2.4

    Args:
        channel_8bit: Integer color value 0-255 (e.g., R=128).

    Returns:
        Linearized channel value as a float between 0.0 and 1.0.
    """
    # Normalize 8-bit to 0.0-1.0
    c = channel_8bit / 255.0

    if c <= 0.04045:
        return c / 12.92
    else:
        return math.pow((c + 0.055) / 1.055, 2.4)


def relative_luminance(r: int, g: int, b: int) -> float:
    """
    Calculate the WCAG 2.1 Relative Luminance of an RGB color.

    Uses CIE colorimetric coefficients:
        L = 0.2126 * R_linear + 0.7152 * G_linear + 0.0722 * B_linear

    Relative luminance ranges from 0 (darkest black) to 1 (lightest white).

    Args:
        r: Red channel (0-255).
        g: Green channel (0-255).
        b: Blue channel (0-255).

    Returns:
        Relative luminance as a float between 0.0 and 1.0.
    """
    r_lin = linearize_srgb_channel(r)
    g_lin = linearize_srgb_channel(g)
    b_lin = linearize_srgb_channel(b)

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color1_rgb: Tuple[int, int, int],
                   color2_rgb: Tuple[int, int, int]) -> float:
    """
    Calculate the WCAG 2.1 Contrast Ratio between two colors.

    The formula is:
        C = (L1 + 0.05) / (L2 + 0.05)

    Where L1 is the relative luminance of the lighter color
    and L2 is the relative luminance of the darker color.

    The result ranges from 1:1 (identical) to 21:1 (black on white).

    Args:
        color1_rgb: (R, G, B) tuple for color 1 (0-255 each).
        color2_rgb: (R, G, B) tuple for color 2 (0-255 each).

    Returns:
        Contrast ratio as a float (e.g., 4.5 for 4.5:1).
    """
    lum1 = relative_luminance(*color1_rgb)
    lum2 = relative_luminance(*color2_rgb)

    # L1 is always the lighter (higher luminance)
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    return (lighter + 0.05) / (darker + 0.05)


def check_contrast(
    fg_color_str: str,
    bg_color_str: str,
    font_size_px: float = 16.0,
    font_weight: int = 400,
) -> ContrastResult:
    """
    Full WCAG 2.1 contrast check between foreground and background colors.

    Determines whether the contrast ratio passes AA and AAA thresholds,
    accounting for large text exceptions.

    Args:
        fg_color_str: CSS foreground (text) color string.
        bg_color_str: CSS background color string.
        font_size_px: Font size in pixels.
        font_weight: CSS font weight (numeric, e.g. 400, 700).

    Returns:
        ContrastResult with all pass/fail information.
    """
    fg = parse_color(fg_color_str)
    bg = parse_color(bg_color_str)

    # Default to black-on-white if parsing fails
    if fg is None:
        fg = (0, 0, 0, 1.0)
    if bg is None:
        bg = (255, 255, 255, 1.0)

    # Alpha compositing: blend semi-transparent foreground over background
    fg_rgb = _alpha_composite(fg, bg)
    bg_rgb = (bg[0], bg[1], bg[2])

    ratio = contrast_ratio(fg_rgb, bg_rgb)

    # Determine if this is "large text" per WCAG 2.1
    is_large = _is_large_text(font_size_px, font_weight)

    passes_aa_normal = ratio >= WCAG_THRESHOLDS["AA_normal"]
    passes_aa_large = ratio >= WCAG_THRESHOLDS["AA_large"]
    passes_aaa_normal = ratio >= WCAG_THRESHOLDS["AAA_normal"]
    passes_aaa_large = ratio >= WCAG_THRESHOLDS["AAA_large"]

    # What level does it actually need to pass?
    if is_large:
        passes_required = passes_aa_large
    else:
        passes_required = passes_aa_normal

    # Determine the highest WCAG level met
    if passes_aaa_normal:
        level_met = "AAA"
    elif passes_aa_normal:
        level_met = "AA"
    elif passes_aa_large and is_large:
        level_met = "AA"
    else:
        level_met = "FAIL"

    return ContrastResult(
        foreground_color=fg_color_str,
        background_color=bg_color_str,
        contrast_ratio=round(ratio, 2),
        passes_aa_normal=passes_aa_normal,
        passes_aa_large=passes_aa_large,
        passes_aaa_normal=passes_aaa_normal,
        passes_aaa_large=passes_aaa_large,
        is_large_text=is_large,
        passes_required=passes_required,
        wcag_level_met=level_met,
    )


def _is_large_text(font_size_px: float, font_weight: int) -> bool:
    """
    Determine if text qualifies as "large text" under WCAG 2.1.

    Large text is defined as:
    - 18pt (24px) or larger for normal weight, OR
    - 14pt (18.67px) or larger for bold weight (>= 700)
    """
    if font_size_px >= LARGE_TEXT_PX:
        return True
    if font_size_px >= LARGE_TEXT_BOLD_PX and font_weight >= BOLD_WEIGHT_THRESHOLD:
        return True
    return False


def _alpha_composite(
    fg: Tuple[int, int, int, float],
    bg: Tuple[int, int, int, float],
) -> Tuple[int, int, int]:
    """
    Alpha-composite a semi-transparent foreground color over a background.

    Uses the standard "over" compositing operation.
    Returns opaque RGB values (0-255).
    """
    fg_a = fg[3] if len(fg) > 3 else 1.0
    if fg_a >= 1.0:
        return (fg[0], fg[1], fg[2])

    # Blend: result = fg * alpha + bg * (1 - alpha)
    r = int(round(fg[0] * fg_a + bg[0] * (1 - fg_a)))
    g = int(round(fg[1] * fg_a + bg[1] * (1 - fg_a)))
    b = int(round(fg[2] * fg_a + bg[2] * (1 - fg_a)))
    return (_clamp(r), _clamp(g), _clamp(b))


# ─────────────────────────────────────────────
# Color Blindness Simulation
# ─────────────────────────────────────────────

# Color blindness simulation matrices (linear RGB)
# These transform normal-vision RGB into simulated color-blind RGB.
# Source: Brettel, Viénot & Mollon (1997) and Viénot, Brettel & Mollon (1999)
COLOR_BLINDNESS_MATRICES = {
    "protanopia": np.array([
        [0.56667, 0.43333, 0.00000],
        [0.55833, 0.44167, 0.00000],
        [0.00000, 0.24167, 0.75833],
    ]),
    "deuteranopia": np.array([
        [0.62500, 0.37500, 0.00000],
        [0.70000, 0.30000, 0.00000],
        [0.00000, 0.30000, 0.70000],
    ]),
    "tritanopia": np.array([
        [0.95000, 0.05000, 0.00000],
        [0.00000, 0.43333, 0.56667],
        [0.00000, 0.47500, 0.52500],
    ]),
}


def simulate_color_blindness(
    r: int, g: int, b: int,
    blindness_type: str = "protanopia",
) -> Tuple[int, int, int]:
    """
    Simulate how a color appears to someone with color vision deficiency.

    Applies a linear transformation matrix to the linearized sRGB values.

    Args:
        r: Red channel (0-255).
        g: Green channel (0-255).
        b: Blue channel (0-255).
        blindness_type: One of "protanopia", "deuteranopia", "tritanopia".

    Returns:
        Simulated (R, G, B) tuple (0-255).
    """
    if blindness_type not in COLOR_BLINDNESS_MATRICES:
        raise ValueError(
            f"Unknown blindness type: '{blindness_type}'. "
            f"Must be one of: {list(COLOR_BLINDNESS_MATRICES.keys())}"
        )

    # Linearize the sRGB channels
    rgb_linear = np.array([
        linearize_srgb_channel(r),
        linearize_srgb_channel(g),
        linearize_srgb_channel(b),
    ])

    # Apply the transformation matrix
    matrix = COLOR_BLINDNESS_MATRICES[blindness_type]
    simulated_linear = matrix @ rgb_linear

    # Clamp to [0, 1] in linear space
    simulated_linear = np.clip(simulated_linear, 0.0, 1.0)

    # Convert back to sRGB (gamma compress)
    simulated_srgb = [_gamma_compress(c) for c in simulated_linear]

    return (
        _clamp(int(round(simulated_srgb[0] * 255))),
        _clamp(int(round(simulated_srgb[1] * 255))),
        _clamp(int(round(simulated_srgb[2] * 255))),
    )


def _gamma_compress(c_linear: float) -> float:
    """
    Apply sRGB gamma compression (inverse of linearization).

    If c_linear <= 0.0031308:
        c_srgb = 12.92 * c_linear
    Else:
        c_srgb = 1.055 * c_linear^(1/2.4) - 0.055
    """
    if c_linear <= 0.0031308:
        return 12.92 * c_linear
    else:
        return 1.055 * math.pow(c_linear, 1.0 / 2.4) - 0.055


def check_contrast_for_color_blind(
    fg_color_str: str,
    bg_color_str: str,
    font_size_px: float = 16.0,
    font_weight: int = 400,
) -> Dict[str, ContrastResult]:
    """
    Check contrast ratios as perceived by users with color vision deficiencies.

    Runs the contrast check for normal vision and all three types of
    color blindness.

    Args:
        fg_color_str: CSS foreground color string.
        bg_color_str: CSS background color string.
        font_size_px: Font size in pixels.
        font_weight: CSS font weight.

    Returns:
        Dict mapping vision type ("normal", "protanopia", etc.) to ContrastResult.
    """
    results = {}

    # Normal vision
    results["normal"] = check_contrast(fg_color_str, bg_color_str, font_size_px, font_weight)

    fg = parse_color(fg_color_str)
    bg = parse_color(bg_color_str)
    if fg is None or bg is None:
        return results

    # For each color blindness type
    for cb_type in COLOR_BLINDNESS_MATRICES:
        sim_fg = simulate_color_blindness(fg[0], fg[1], fg[2], cb_type)
        sim_bg = simulate_color_blindness(bg[0], bg[1], bg[2], cb_type)

        sim_fg_str = f"rgb({sim_fg[0]}, {sim_fg[1]}, {sim_fg[2]})"
        sim_bg_str = f"rgb({sim_bg[0]}, {sim_bg[1]}, {sim_bg[2]})"

        results[cb_type] = check_contrast(sim_fg_str, sim_bg_str, font_size_px, font_weight)

    return results


# ─────────────────────────────────────────────
# Suggest Fix Colors
# ─────────────────────────────────────────────

def suggest_fix_color(
    fg_color_str: str,
    bg_color_str: str,
    target_ratio: float = 4.5,
) -> Optional[str]:
    """
    Suggest a darker or lighter foreground color that meets the target contrast.

    Strategy: Progressively darken or lighten the foreground color until
    the contrast ratio meets the target threshold.

    Args:
        fg_color_str: Current foreground (text) CSS color string.
        bg_color_str: Background CSS color string.
        target_ratio: Desired minimum contrast ratio (default 4.5 for AA).

    Returns:
        A hex color string for a suggested fix, or None if no fix is found.
    """
    fg = parse_color(fg_color_str)
    bg = parse_color(bg_color_str)

    if fg is None or bg is None:
        return None

    fg_rgb = (fg[0], fg[1], fg[2])
    bg_rgb = (bg[0], bg[1], bg[2])

    bg_lum = relative_luminance(*bg_rgb)

    # Try darkening the foreground (towards black)
    for step in range(256):
        candidate = (
            max(0, fg_rgb[0] - step),
            max(0, fg_rgb[1] - step),
            max(0, fg_rgb[2] - step),
        )
        ratio = contrast_ratio(candidate, bg_rgb)
        if ratio >= target_ratio:
            return f"#{candidate[0]:02x}{candidate[1]:02x}{candidate[2]:02x}"

    # Try lightening the foreground (towards white)
    for step in range(256):
        candidate = (
            min(255, fg_rgb[0] + step),
            min(255, fg_rgb[1] + step),
            min(255, fg_rgb[2] + step),
        )
        ratio = contrast_ratio(candidate, bg_rgb)
        if ratio >= target_ratio:
            return f"#{candidate[0]:02x}{candidate[1]:02x}{candidate[2]:02x}"

    return None


# ─────────────────────────────────────────────
# Full WCAG Audit on Computed Styles
# ─────────────────────────────────────────────

def _parse_font_size_px(font_size_str: str) -> float:
    """Extract numeric pixel value from a CSS font-size string like '16px'."""
    if not font_size_str:
        return 16.0
    match = re.match(r"([\d.]+)", font_size_str)
    if match:
        return float(match.group(1))
    return 16.0


def _parse_font_weight(font_weight_str: str) -> int:
    """Convert CSS font-weight string to numeric value."""
    if not font_weight_str:
        return 400
    # Handle keyword weights
    weight_map = {
        "normal": 400, "bold": 700,
        "lighter": 300, "bolder": 700,
    }
    fw_lower = font_weight_str.strip().lower()
    if fw_lower in weight_map:
        return weight_map[fw_lower]
    try:
        return int(float(font_weight_str))
    except (ValueError, TypeError):
        return 400


def audit_computed_styles(
    computed_styles: List[dict],
    url: str = "",
    check_aaa: bool = False,
) -> AccessibilityAuditResult:
    """
    Run a full WCAG 2.1 contrast audit on computed styles from the BrowserEngine.

    This function takes the output of BrowserEngine.extract_computed_styles()
    and evaluates every text element for WCAG 2.1 color contrast compliance.

    Args:
        computed_styles: List of dicts from BrowserEngine.extract_computed_styles().
            Each dict has: tag, text, color, backgroundColor, fontSize,
            fontWeight, boundingBox, selector.
        url: The URL being audited (for reporting).
        check_aaa: If True, also flag AAA violations (not just AA).

    Returns:
        AccessibilityAuditResult with all violations found.
    """
    result = AccessibilityAuditResult(url=url)
    violations = []

    for element in computed_styles:
        result.total_elements_checked += 1

        fg_color = element.get("color", "")
        bg_color = element.get("backgroundColor", "")

        # Skip elements where we can't determine both colors
        if not fg_color or not bg_color:
            continue

        # Skip transparent backgrounds (they inherit from parent,
        # and computed styles from Playwright should already resolve this)
        fg_parsed = parse_color(fg_color)
        bg_parsed = parse_color(bg_color)
        if fg_parsed is None or bg_parsed is None:
            continue

        # Skip fully transparent elements
        if bg_parsed[3] == 0.0 and bg_color.startswith("rgba"):
            # When background is transparent, assume white as the worst case
            bg_color = "rgb(255, 255, 255)"

        font_size_px = _parse_font_size_px(element.get("fontSize", "16px"))
        font_weight = _parse_font_weight(element.get("fontWeight", "400"))

        contrast = check_contrast(fg_color, bg_color, font_size_px, font_weight)

        # Check AA compliance (the minimum required level)
        if not contrast.passes_required:
            required_ratio = (
                WCAG_THRESHOLDS["AA_large"]
                if contrast.is_large_text
                else WCAG_THRESHOLDS["AA_normal"]
            )

            # Determine severity based on how badly it fails
            if contrast.contrast_ratio < 2.0:
                severity = Severity.CRITICAL.value
            elif contrast.contrast_ratio < 3.0:
                severity = Severity.HIGH.value
            elif contrast.contrast_ratio < required_ratio:
                severity = Severity.MEDIUM.value
            else:
                severity = Severity.LOW.value

            # Generate a helpful suggestion
            suggested_color = suggest_fix_color(fg_color, bg_color, required_ratio)
            suggestion = (
                f"Change text color to {suggested_color} to achieve "
                f"a contrast ratio of at least {required_ratio}:1."
                if suggested_color
                else f"Increase contrast ratio to at least {required_ratio}:1."
            )

            violation = ContrastViolation(
                element_tag=element.get("tag", "unknown"),
                element_text=element.get("text", "")[:100],
                element_selector=element.get("selector", ""),
                foreground_color=fg_color,
                background_color=bg_color,
                contrast_ratio=contrast.contrast_ratio,
                required_ratio=required_ratio,
                wcag_criterion="1.4.3 Contrast (Minimum)",
                wcag_level="AA",
                severity=severity,
                suggestion=suggestion,
                bounding_box=element.get("boundingBox"),
                font_size=element.get("fontSize", ""),
                font_weight=element.get("fontWeight", ""),
                is_large_text=contrast.is_large_text,
            )
            violations.append(violation)

        # Optionally check AAA
        if check_aaa and contrast.passes_required and not contrast.passes_aaa_normal:
            aaa_required = (
                WCAG_THRESHOLDS["AAA_large"]
                if contrast.is_large_text
                else WCAG_THRESHOLDS["AAA_normal"]
            )

            if contrast.contrast_ratio < aaa_required:
                suggested_color = suggest_fix_color(fg_color, bg_color, aaa_required)
                suggestion = (
                    f"For AAA compliance, change text color to {suggested_color}."
                    if suggested_color
                    else f"Increase contrast ratio to at least {aaa_required}:1 for AAA."
                )

                violation = ContrastViolation(
                    element_tag=element.get("tag", "unknown"),
                    element_text=element.get("text", "")[:100],
                    element_selector=element.get("selector", ""),
                    foreground_color=fg_color,
                    background_color=bg_color,
                    contrast_ratio=contrast.contrast_ratio,
                    required_ratio=aaa_required,
                    wcag_criterion="1.4.6 Contrast (Enhanced)",
                    wcag_level="AAA",
                    severity=Severity.LOW.value,
                    suggestion=suggestion,
                    bounding_box=element.get("boundingBox"),
                    font_size=element.get("fontSize", ""),
                    font_weight=element.get("fontWeight", ""),
                    is_large_text=contrast.is_large_text,
                )
                violations.append(violation)

    # Populate the result
    result.contrast_violations = violations
    result.total_violations = len(violations)
    result.critical_count = sum(1 for v in violations if v.severity == Severity.CRITICAL.value)
    result.high_count = sum(1 for v in violations if v.severity == Severity.HIGH.value)
    result.medium_count = sum(1 for v in violations if v.severity == Severity.MEDIUM.value)
    result.low_count = sum(1 for v in violations if v.severity == Severity.LOW.value)

    if result.total_elements_checked > 0:
        passing = result.total_elements_checked - sum(
            1 for v in violations if v.wcag_level == "AA"
        )
        result.overall_score = round(
            (passing / result.total_elements_checked) * 100, 1
        )

    logger.info(
        f"WCAG Audit: {result.total_elements_checked} elements checked, "
        f"{result.total_violations} violations found "
        f"(Critical={result.critical_count}, High={result.high_count}, "
        f"Medium={result.medium_count}, Low={result.low_count}). "
        f"Score: {result.overall_score}%"
    )

    return result
