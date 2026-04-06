"""Config flow for the Bosch CT200 integration."""

from __future__ import annotations

import base64
import hashlib
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import ACCESS_TOKEN, DEVICE_ID, DOMAIN, REFRESH_TOKEN, UUID

_LOGGER = logging.getLogger(__name__)


class BoschFlowHandler(config_entries.ConfigFlow):
    """Handle a Bosch CT200 config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize the OAuth2-only config flow."""
        self._auth_code: str | None = None
        self._code_verifier: str | None = None

    def _extract_code_from_input(self, user_input: str) -> str:
        """Extract the authorization code from a pasted redirect URL or raw code."""
        import urllib.parse

        user_input = user_input.strip()
        if not user_input:
            return ""

        if "://" in user_input or user_input.startswith("com.bosch"):
            try:
                params = urllib.parse.parse_qs(urllib.parse.urlsplit(user_input).query)
            except ValueError:
                return ""

            return params.get("code", [""])[0].strip()

        return user_input

    def _map_oauth_exchange_error(self, err: ConfigEntryAuthFailed) -> str:
        """Map token exchange failures to the most specific manual-flow error."""
        message = str(err).strip().casefold()

        if not message:
            return "auth_failed"

        if "cannot connect" in message or "network" in message or "timeout" in message:
            return "network_error"

        if "invalid response" in message or "server" in message:
            return "auth_failed"

        return "invalid_code"

    def _build_code_challenge(self) -> str:
        """Build the PKCE challenge for the current verifier."""
        assert self._code_verifier is not None
        challenge_bytes = hashlib.sha256(self._code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(challenge_bytes).decode().rstrip("=")

    def _show_oauth_browser_form(self, errors: dict[str, str] | None = None):
        """Render the manual browser/code entry step."""
        from .oauth_helper import build_auth_url

        if self._code_verifier is None:
            from .oauth_helper import generate_pkce_pair

            self._code_verifier, code_challenge = generate_pkce_pair()
        else:
            code_challenge = self._build_code_challenge()

        return self.async_show_form(
            step_id="oauth_browser",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors or {},
            description_placeholders={"auth_url": build_auth_url(code_challenge)},
        )

    async def async_step_user(self, user_input=None):
        """Start the OAuth browser/code flow immediately."""
        return await self.async_step_oauth_browser(user_input)

    async def async_step_oauth_browser(self, user_input=None):
        """Show the OAuth authorization URL and collect the authorization code."""
        if user_input is None:
            return self._show_oauth_browser_form()

        auth_input = user_input.get("code", "").strip()
        if not auth_input:
            return self._show_oauth_browser_form(errors={"code": "no_code"})

        auth_code = self._extract_code_from_input(auth_input)
        if not auth_code:
            return self._show_oauth_browser_form(errors={"code": "no_code"})

        self._auth_code = auth_code
        return await self.async_step_oauth_exchange()

    async def async_step_oauth_exchange(self, user_input=None):
        """Exchange the authorization code for tokens and discover the device."""
        from .pointt_rest_client import PointTRestClient, exchange_code_for_tokens

        del user_input

        try:
            session = async_get_clientsession(self.hass)
            access_token, refresh_token = await exchange_code_for_tokens(
                session=session,
                code=self._auth_code,
                code_verifier=self._code_verifier,
            )

            temp_client = PointTRestClient(
                session=session,
                device_id="",
                access_token=access_token,
                refresh_token=refresh_token,
            )
            gateways = await temp_client.get_gateways()

            if not gateways:
                _LOGGER.error("No gateways found for this account")
                return self._show_oauth_browser_form(errors={"base": "no_devices"})

            gateway = gateways[0]
            device_id = gateway["deviceId"]

            client = PointTRestClient(
                session=session,
                device_id=device_id,
                access_token=access_token,
                refresh_token=refresh_token,
            )
            device_info = await client.get_device_info()
            uuid = device_info.get("uuid", device_id)

            await self.async_set_unique_id(uuid)
            self._abort_if_unique_id_configured()

            _LOGGER.debug("Adding Bosch OAuth2 entry.")
            return self.async_create_entry(
                title=f"Bosch CT200 ({device_id})",
                data={
                    DEVICE_ID: device_id,
                    UUID: uuid,
                    ACCESS_TOKEN: access_token,
                    REFRESH_TOKEN: refresh_token,
                },
            )
        except ConfigEntryAuthFailed as err:
            _LOGGER.error("OAuth token exchange failed: %s", err)
            return self._show_oauth_browser_form(
                errors={"base": self._map_oauth_exchange_error(err)}
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error during OAuth setup: %s", err)
            return self._show_oauth_browser_form(errors={"base": "auth_failed"})


config_entries.HANDLERS.register(DOMAIN)(BoschFlowHandler)
