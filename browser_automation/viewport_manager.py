"""
VisionGuard AI - Viewport Manager
==================================
Manages standardized viewport configurations for multi-device
accessibility testing. Each viewport simulates a real-world device
resolution used in responsive web design.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ViewportConfig:
    """Immutable viewport configuration for a device type."""
    name: str
    width: int
    height: int
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    description: str = ""


class ViewportManager:
    """
    Manages viewport configurations for multi-device testing.
    
    Provides standardized device profiles that match real-world
    screen resolutions used in WCAG 2.1 responsive testing.
    """
    
    # Standard viewport presets based on real device data
    _PRESETS: Dict[str, ViewportConfig] = {
        "desktop_1080p": ViewportConfig(
            name="desktop_1080p",
            width=1920, height=1080,
            description="Standard Full HD Desktop Monitor"
        ),
        "desktop_720p": ViewportConfig(
            name="desktop_720p",
            width=1366, height=768,
            description="Common Laptop Display (most popular desktop resolution)"
        ),
        "tablet_landscape": ViewportConfig(
            name="tablet_landscape",
            width=1024, height=768,
            is_mobile=True, has_touch=True,
            description="iPad / Generic Tablet in Landscape"
        ),
        "tablet_portrait": ViewportConfig(
            name="tablet_portrait",
            width=768, height=1024,
            is_mobile=True, has_touch=True,
            description="iPad / Generic Tablet in Portrait"
        ),
        "mobile_large": ViewportConfig(
            name="mobile_large",
            width=414, height=896,
            device_scale_factor=2.0,
            is_mobile=True, has_touch=True,
            description="iPhone 11 / XR (large mobile)"
        ),
        "mobile_standard": ViewportConfig(
            name="mobile_standard",
            width=375, height=812,
            device_scale_factor=3.0,
            is_mobile=True, has_touch=True,
            description="iPhone X / 12 / 13 (standard mobile)"
        ),
        "mobile_small": ViewportConfig(
            name="mobile_small",
            width=360, height=640,
            device_scale_factor=2.0,
            is_mobile=True, has_touch=True,
            description="Samsung Galaxy S series / common Android"
        ),
    }

    @classmethod
    def get_viewport(cls, device_type: str) -> Optional[ViewportConfig]:
        """
        Returns the ViewportConfig for a given device type key.
        
        Args:
            device_type: Key from the presets (e.g., 'mobile_standard').
            
        Returns:
            ViewportConfig or None if key is invalid.
        """
        return cls._PRESETS.get(device_type)

    @classmethod
    def get_all_viewports(cls) -> Dict[str, ViewportConfig]:
        """Returns all configured viewport presets."""
        return dict(cls._PRESETS)

    @classmethod
    def get_viewport_names(cls) -> List[str]:
        """Returns a list of all available viewport preset names."""
        return list(cls._PRESETS.keys())

    @classmethod
    def get_default_audit_viewports(cls) -> Dict[str, ViewportConfig]:
        """
        Returns the recommended subset of viewports for a standard
        WCAG accessibility audit: Desktop, Tablet, and Mobile.
        This covers the 3 critical breakpoints.
        """
        default_keys = ["desktop_1080p", "tablet_portrait", "mobile_standard"]
        return {k: cls._PRESETS[k] for k in default_keys}

    @classmethod
    def to_playwright_context_options(cls, config: ViewportConfig) -> dict:
        """
        Converts a ViewportConfig into the dictionary format expected
        by Playwright's browser.new_context() method.
        
        Args:
            config: A ViewportConfig dataclass instance.
            
        Returns:
            Dict compatible with playwright's new_context kwargs.
        """
        return {
            "viewport": {"width": config.width, "height": config.height},
            "device_scale_factor": config.device_scale_factor,
            "is_mobile": config.is_mobile,
            "has_touch": config.has_touch,
        }
