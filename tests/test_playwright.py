import pytest
from browser_automation.browser_engine import BrowserEngine

@pytest.mark.asyncio
async def test_authentication_injection():
    """Verifies that the browser engine successfully injects cookies for authentication."""
    engine = BrowserEngine(headless=True)
    
    auth_cookies = [
        {
            "name": "visionguard_session_token",
            "value": "super_secret_auth_123",
            "domain": "httpbin.org",
            "path": "/"
        }
    ]
    
    html_output = await engine.get_page_html(
        url="https://httpbin.org/cookies", 
        cookies=auth_cookies
    )
    
    # Pytest will automatically fail if this condition is not met
    assert "super_secret_auth_123" in html_output, "Cookie was not injected successfully!"