"""PointT REST API client for OAuth2 authentication."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_TOKEN_URL,
    POINTT_API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)

BULK_URL = f"{POINTT_API_BASE_URL}/pointt-api/api/v1/bulk"


async def exchange_code_for_tokens(
    session: aiohttp.ClientSession,
    code: str,
    code_verifier: str,
) -> tuple[str, str]:
    """Exchange authorization code for access and refresh tokens.

    Args:
        session: aiohttp ClientSession
        code: Authorization code from OAuth redirect
        code_verifier: PKCE code verifier

    Returns:
        tuple: (access_token, refresh_token)

    Raises:
        ConfigEntryAuthFailed: If token exchange fails
    """
    data = {
        'grant_type': 'authorization_code',
        'client_id': OAUTH_CLIENT_ID,
        'code': code,
        'redirect_uri': OAUTH_REDIRECT_URI,
        'code_verifier': code_verifier,
    }

    try:
        async with session.post(OAUTH_TOKEN_URL, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                _LOGGER.error("Token exchange failed: %s", error_text)
                raise ConfigEntryAuthFailed("Failed to exchange authorization code")

            token_data = await response.json()
            try:
                return token_data['access_token'], token_data['refresh_token']
            except KeyError as err:
                _LOGGER.error("Invalid token response: %s", err)
                raise ConfigEntryAuthFailed("Invalid response from authentication server") from err

    except aiohttp.ClientError as err:
        _LOGGER.error("Network error during token exchange: %s", err)
        raise ConfigEntryAuthFailed("Cannot connect to authentication server") from err


class PointTRestClient:
    """Client for PointT REST API with OAuth2 token management."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        device_id: str,
        access_token: str,
        refresh_token: str,
        token_update_callback=None,
    ):
        """Initialize the PointT REST client.

        Args:
            session: aiohttp ClientSession for making requests
            device_id: The Bosch gateway device ID
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token for token renewal
            token_update_callback: Optional async callback to persist updated tokens
                                   Called with (access_token, refresh_token) after refresh
        """
        self._session = session
        self.device_id = device_id
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_update_callback = token_update_callback
        self.base_url = POINTT_API_BASE_URL

    async def refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token.

        Returns:
            str: The new access token

        Raises:
            ConfigEntryAuthFailed: If token refresh fails
        """
        data = {
            'grant_type': 'refresh_token',
            'client_id': OAUTH_CLIENT_ID,
            'refresh_token': self._refresh_token,
        }
        try:
            async with self._session.post(OAUTH_TOKEN_URL, data=data) as response:
                if response.status == 403:
                    _LOGGER.error("Refresh token invalid or expired")
                    raise ConfigEntryAuthFailed("Refresh token expired - re-authentication required")
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Token refresh failed: %s", error_text)
                    raise ConfigEntryAuthFailed("Failed to refresh access token")
                token_data = await response.json()
                self._access_token = token_data['access_token']
                self._refresh_token = token_data.get('refresh_token', self._refresh_token)
                _LOGGER.debug("Access token refreshed successfully")

                # Persist updated tokens to config entry
                if self._token_update_callback:
                    await self._token_update_callback(self._access_token, self._refresh_token)
                    _LOGGER.debug("Updated tokens saved to config entry")

                return self._access_token
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during token refresh: %s", err)
            raise ConfigEntryAuthFailed("Cannot connect to authentication server") from err

    async def get_resource(self, path: str) -> dict[str, Any] | None:
        """Get a resource from the PointT API.

        Automatically refreshes token on 401 and retries.

        Args:
            path: API endpoint path (e.g., "/zones/zn1/currentTemperature")

        Returns:
            dict: Resource data, or None if not found (404)

        Raises:
            aiohttp.ClientError: If API request fails
            asyncio.TimeoutError: If request times out
        """
        url = f"{self.base_url}/pointt-api/api/v1/gateways/{self.device_id}/resource{path}"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            async with self._session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                _LOGGER.debug("Access token expired, refreshing...")
                await self.refresh_access_token()
                headers = {"Authorization": f"Bearer {self._access_token}"}
                async with self._session.get(url, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    return await response.json()
            elif err.status == 404:
                _LOGGER.debug("Resource not found: %s", path)
                return None
            elif err.status in (403, 412):
                # 403 Forbidden - endpoint not accessible (common during discovery)
                # 412 Precondition Failed - endpoint requires conditions not met
                _LOGGER.debug("Resource not available (%s): %s", err.status, path)
                return None
            else:
                _LOGGER.error("API error getting resource %s: %s", path, err)
                raise
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout getting resource: %s", path)
            raise

    async def set_resource(self, path: str, value: Any) -> bool:
        """Set a resource value in the PointT API.

        Automatically refreshes token on 401 and retries.

        Args:
            path: API endpoint path (e.g., "/zones/zn1/temperatureHeatingSetpoint")
            value: The value to set

        Returns:
            bool: True if successful

        Raises:
            aiohttp.ClientError: If API request fails
            asyncio.TimeoutError: If request times out
        """
        url = f"{self.base_url}/pointt-api/api/v1/gateways/{self.device_id}/resource{path}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }
        try:
            async with self._session.put(
                url, headers=headers, json={"value": value}, timeout=10
            ) as response:
                response.raise_for_status()
                return True
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                _LOGGER.debug("Access token expired, refreshing...")
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                async with self._session.put(
                    url, headers=headers, json={"value": value}, timeout=10
                ) as response:
                    response.raise_for_status()
                    return True
            else:
                _LOGGER.error("API error setting resource %s: %s", path, err)
                raise
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout setting resource: %s", path)
            raise

    async def get_gateways(self) -> list[dict[str, Any]]:
        """Get list of available gateways for this account.

        Returns:
            List of gateway dicts with deviceId and deviceType

        Raises:
            ConfigEntryAuthFailed: If authentication fails
        """
        url = f"{self.base_url}/pointt-api/api/v1/gateways/"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            async with self._session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                # Token expired, refresh and retry
                await self.refresh_access_token()
                headers = {"Authorization": f"Bearer {self._access_token}"}
                async with self._session.get(url, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                _LOGGER.error("API error getting gateways: %s", err)
                raise

    async def post_bulk_resources(self, resource_paths: list[str]) -> list[dict[str, Any]]:
        """Fetch multiple resources through the PointT bulk endpoint."""
        payload = [{"gatewayId": self.device_id, "resourcePaths": resource_paths}]
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.post(
                BULK_URL, headers=headers, json=payload, timeout=15
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data if isinstance(data, list) else []
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                _LOGGER.debug("Access token expired, refreshing before bulk request...")
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                async with self._session.post(
                    BULK_URL, headers=headers, json=payload, timeout=15
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data if isinstance(data, list) else []
            _LOGGER.error("Bulk API request failed: %s", err)
            raise

    async def get_device_info(self) -> dict[str, Any]:
        """Get basic device information.

        Returns:
            Dict with uuid, firmware, and product_id
        """
        uuid_data = await self.get_resource("/gateway/uuid")
        firmware_data = await self.get_resource("/gateway/versionFirmware")
        product_data = await self.get_resource("/gateway/productID")

        return {
            "uuid": uuid_data.get("value") if uuid_data else None,
            "firmware": firmware_data.get("value") if firmware_data else None,
            "product_id": product_data.get("value") if product_data else None,
        }
