"""OAuth2 helper utilities for Bosch integration."""
import base64
import hashlib
import secrets
import urllib.parse

from .const import (
    OAUTH_CLIENT_ID,
    OAUTH_LOGIN_FLOW_ID,
    OAUTH_LOGIN_URL,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPES,
)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge pair.

    Returns:
        tuple: (code_verifier, code_challenge)
    """
    # Generate random 32-byte code verifier
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')

    # Create SHA256 hash challenge
    challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')

    return code_verifier, code_challenge


def build_auth_url(code_challenge: str) -> str:
    """Build the Bosch SingleKey login URL used by the mobile flow.

    Args:
        code_challenge: The PKCE code challenge

    Returns:
        Full authorization URL
    """
    params = {
        "redirect_uri": urllib.parse.quote_plus(OAUTH_REDIRECT_URI),
        "client_id": OAUTH_CLIENT_ID,
        "response_type": "code",
        "prompt": "login",
        "state": secrets.token_urlsafe(18),
        "nonce": secrets.token_urlsafe(18),
        "scope": urllib.parse.quote(OAUTH_SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "style_id": "tt_bsch",
        "suppressed_prompt": "login",
    }
    inner_query = urllib.parse.unquote(urllib.parse.urlencode(params))
    return_url = urllib.parse.quote(
        f"/auth/connect/authorize/callback?{inner_query}",
        safe="",
    )
    return f"{OAUTH_LOGIN_URL}?ReturnUrl={return_url}&f={OAUTH_LOGIN_FLOW_ID}"
