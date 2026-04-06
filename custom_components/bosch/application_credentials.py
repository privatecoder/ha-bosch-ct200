"""Application credentials platform for Bosch CT200 OAuth2."""
from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import OAUTH_AUTH_URL, OAUTH_TOKEN_URL


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server for Bosch SingleKey ID."""
    return AuthorizationServer(
        authorize_url=OAUTH_AUTH_URL,
        token_url=OAUTH_TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return description placeholders for the credentials dialog."""
    return {
        "more_info_url": "https://github.com/privatecoder/ha-bosch-ct200",
        "oauth_info": (
            "Note: This integration uses the PointT REST API which requires "
            "OAuth2 authentication through Bosch SingleKey ID. You'll need to "
            "use the pre-configured client credentials or register your own "
            "application if Bosch provides a developer portal."
        ),
    }
