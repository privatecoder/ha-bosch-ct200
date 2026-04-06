"""Tests for OAuth2 helper utilities."""
import sys
import re
import importlib.util
from pathlib import Path
from types import ModuleType

# Load oauth_helper module directly without triggering package __init__.py
oauth_helper_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "oauth_helper.py"
custom_components_pkg = ModuleType("custom_components")
bosch_pkg = ModuleType("custom_components.bosch")
bosch_pkg.__path__ = [str(oauth_helper_path.parent)]
sys.modules.setdefault("custom_components", custom_components_pkg)
sys.modules["custom_components.bosch"] = bosch_pkg

spec = importlib.util.spec_from_file_location(
    "custom_components.bosch.oauth_helper",
    oauth_helper_path,
)
oauth_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oauth_helper)

generate_pkce_pair = oauth_helper.generate_pkce_pair
build_auth_url = oauth_helper.build_auth_url


def test_generate_pkce_pair():
    """Test PKCE code verifier and challenge generation."""
    verifier, challenge = generate_pkce_pair()

    # Verifier should be 43-128 characters, URL-safe base64
    assert 43 <= len(verifier) <= 128
    assert re.match(r'^[A-Za-z0-9_-]+$', verifier)

    # Challenge should be 43 characters (base64url of SHA256)
    assert len(challenge) == 43
    assert re.match(r'^[A-Za-z0-9_-]+$', challenge)

    # Each call should produce different codes
    verifier2, challenge2 = generate_pkce_pair()
    assert verifier != verifier2
    assert challenge != challenge2


def test_pkce_challenge_format():
    """Test that challenge is properly formatted base64url SHA256."""
    import hashlib
    import base64

    verifier, challenge = generate_pkce_pair()

    # Manually compute challenge to verify
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip('=')

    assert challenge == expected_challenge


def test_build_auth_url():
    """Test authorization URL building."""
    challenge = "test_challenge_string_123"
    url = build_auth_url(challenge)

    assert url.startswith("https://singlekey-id.com/de-de/login?ReturnUrl=")
    assert "client_id%3D762162C0-FA2D-4540-AE66-6489F189FADC" in url
    assert "code_challenge%3Dtest_challenge_string_123" in url
    assert "code_challenge_method%3DS256" in url
    assert "response_type%3Dcode" in url
    assert "style_id%3Dtt_bsch" in url
    assert "suppressed_prompt%3Dlogin" in url
    assert "offline_access" in url
