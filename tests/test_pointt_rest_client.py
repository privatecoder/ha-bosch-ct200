"""Tests for PointT REST API client."""
import sys
import pytest
import aiohttp
from aiohttp import ClientSession
from unittest.mock import AsyncMock, MagicMock
import importlib.util
from pathlib import Path
from types import ModuleType

# Load pointt_rest_client module directly without triggering package __init__.py
pointt_rest_client_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "pointt_rest_client.py"
custom_components_pkg = ModuleType("custom_components")
bosch_pkg = ModuleType("custom_components.bosch")
bosch_pkg.__path__ = [str(pointt_rest_client_path.parent)]
sys.modules.setdefault("custom_components", custom_components_pkg)
sys.modules["custom_components.bosch"] = bosch_pkg

spec = importlib.util.spec_from_file_location(
    "custom_components.bosch.pointt_rest_client",
    pointt_rest_client_path,
)
pointt_rest_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pointt_rest_client)

PointTRestClient = pointt_rest_client.PointTRestClient


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    return MagicMock(spec=ClientSession)


def test_client_initialization(mock_session):
    """Test client initializes with correct parameters."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="test_access_token",
        refresh_token="test_refresh_token"
    )

    assert client.device_id == "101270435"
    assert client._access_token == "test_access_token"
    assert client._refresh_token == "test_refresh_token"
    assert client._session == mock_session
    assert client.base_url == "https://pointt-api.bosch-thermotechnology.com"


@pytest.mark.asyncio
async def test_exchange_code_for_tokens(mock_session):
    """Test exchanging authorization code for tokens."""
    exchange_code_for_tokens = pointt_rest_client.exchange_code_for_tokens

    # Mock successful token response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer"
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    # Make session.post return the mock response
    mock_session.post = MagicMock(return_value=mock_response)

    access_token, refresh_token = await exchange_code_for_tokens(
        session=mock_session,
        code="test_auth_code",
        code_verifier="test_verifier"
    )

    assert access_token == "new_access_token"
    assert refresh_token == "new_refresh_token"

    # Verify correct API call was made
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert call_args[0][0] == "https://singlekey-id.com/auth/connect/token"

    # Verify POST data payload
    assert call_args[1]['data']['grant_type'] == 'authorization_code'
    assert call_args[1]['data']['code'] == 'test_auth_code'
    assert call_args[1]['data']['code_verifier'] == 'test_verifier'
    assert call_args[1]['data']['client_id'] == '762162C0-FA2D-4540-AE66-6489F189FADC'
    assert call_args[1]['data']['redirect_uri'] == 'com.bosch.tt.dashtt.pointt://app/login'


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_non_200_response(mock_session):
    """Test token exchange handles non-200 HTTP responses."""
    from homeassistant.exceptions import ConfigEntryAuthFailed
    exchange_code_for_tokens = pointt_rest_client.exchange_code_for_tokens

    # Mock error response
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad Request: invalid code")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.post = MagicMock(return_value=mock_response)

    # Should raise ConfigEntryAuthFailed
    with pytest.raises(ConfigEntryAuthFailed, match="Failed to exchange authorization code"):
        await exchange_code_for_tokens(
            session=mock_session,
            code="invalid_code",
            code_verifier="test_verifier"
        )


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_network_error(mock_session):
    """Test token exchange handles network errors."""
    from homeassistant.exceptions import ConfigEntryAuthFailed
    exchange_code_for_tokens = pointt_rest_client.exchange_code_for_tokens

    # Mock network error
    mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection timeout"))

    # Should raise ConfigEntryAuthFailed
    with pytest.raises(ConfigEntryAuthFailed, match="Cannot connect to authentication server"):
        await exchange_code_for_tokens(
            session=mock_session,
            code="test_code",
            code_verifier="test_verifier"
        )


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_invalid_json_response(mock_session):
    """Test token exchange handles invalid JSON response (missing keys)."""
    from homeassistant.exceptions import ConfigEntryAuthFailed
    exchange_code_for_tokens = pointt_rest_client.exchange_code_for_tokens

    # Mock response with missing token keys
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "expires_in": 3600,
        "token_type": "Bearer"
        # Missing access_token and refresh_token
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.post = MagicMock(return_value=mock_response)

    # Should raise ConfigEntryAuthFailed
    with pytest.raises(ConfigEntryAuthFailed, match="Invalid response from authentication server"):
        await exchange_code_for_tokens(
            session=mock_session,
            code="test_code",
            code_verifier="test_verifier"
        )


@pytest.mark.asyncio
async def test_refresh_access_token(mock_session):
    """Test refreshing an expired access token."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="old_token",
        refresh_token="refresh_token_123"
    )

    # Mock successful token response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    # Mock post method to return the context manager properly
    mock_session.post = MagicMock(return_value=mock_response)

    new_token = await client.refresh_access_token()

    assert new_token == "new_access_token"
    assert client._access_token == "new_access_token"
    assert client._refresh_token == "new_refresh_token"


@pytest.mark.asyncio
async def test_get_resource_success(mock_session):
    """Test getting a resource successfully."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="test_access_token",
        refresh_token="refresh_token_123"
    )

    # Mock successful resource response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "value": 21.5,
        "type": "float"
    })
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.get = MagicMock(return_value=mock_response)

    result = await client.get_resource("/zones/zn1/currentTemperature")

    assert result == {"value": 21.5, "type": "float"}
    # Verify correct URL and headers
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert "/zones/zn1/currentTemperature" in call_args[0][0]
    assert "Bearer test_access_token" in call_args[1]["headers"]["Authorization"]


@pytest.mark.asyncio
async def test_get_resource_with_token_refresh_on_401(mock_session):
    """Test get_resource refreshes token on 401 and retries."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="old_token",
        refresh_token="refresh_token_123"
    )

    # Mock token refresh response
    token_response = AsyncMock()
    token_response.status = 200
    token_response.json = AsyncMock(return_value={
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600
    })
    token_response.__aenter__ = AsyncMock(return_value=token_response)
    token_response.__aexit__ = AsyncMock(return_value=None)

    # Mock first get response (401 Unauthorized)
    error_response = AsyncMock()
    error_response.status = 401
    error_response.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=401,
            message="Unauthorized",
            headers={}
        )
    )
    error_response.__aenter__ = AsyncMock(return_value=error_response)
    error_response.__aexit__ = AsyncMock(return_value=None)

    # Mock second get response (success after token refresh)
    success_response = AsyncMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value={
        "value": 21.5,
        "type": "float"
    })
    success_response.raise_for_status = MagicMock()
    success_response.__aenter__ = AsyncMock(return_value=success_response)
    success_response.__aexit__ = AsyncMock(return_value=None)

    # Setup mock_session.post for token refresh and get for resource requests
    mock_session.post = MagicMock(return_value=token_response)
    mock_session.get = MagicMock(side_effect=[error_response, success_response])

    result = await client.get_resource("/zones/zn1/currentTemperature")

    # Verify result
    assert result == {"value": 21.5, "type": "float"}
    # Verify token was refreshed
    assert client._access_token == "new_access_token"
    # Verify get was called twice (first 401, then retry after refresh)
    assert mock_session.get.call_count == 2
    # Verify post was called once (token refresh)
    assert mock_session.post.call_count == 1


@pytest.mark.asyncio
async def test_get_resource_404_not_found(mock_session):
    """Test get_resource returns None for 404."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="test_access_token",
        refresh_token="refresh_token_123"
    )

    # Mock 404 response
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
            headers={}
        )
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.get = MagicMock(return_value=mock_response)

    result = await client.get_resource("/invalid/path")

    assert result is None


@pytest.mark.asyncio
async def test_set_resource_success(mock_session):
    """Test setting a resource successfully."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="test_access_token",
        refresh_token="refresh_token_123"
    )

    # Mock successful put response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.put = MagicMock(return_value=mock_response)

    result = await client.set_resource("/zones/zn1/temperatureHeatingSetpoint", 21.5)

    assert result is True
    # Verify correct URL, headers, and payload
    mock_session.put.assert_called_once()
    call_args = mock_session.put.call_args
    assert "/zones/zn1/temperatureHeatingSetpoint" in call_args[0][0]
    assert "Bearer test_access_token" in call_args[1]["headers"]["Authorization"]
    assert call_args[1]["json"] == {"value": 21.5}


@pytest.mark.asyncio
async def test_set_resource_with_token_refresh_on_401(mock_session):
    """Test set_resource refreshes token on 401 and retries."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="old_token",
        refresh_token="refresh_token_123"
    )

    # Mock token refresh response
    token_response = AsyncMock()
    token_response.status = 200
    token_response.json = AsyncMock(return_value={
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600
    })
    token_response.__aenter__ = AsyncMock(return_value=token_response)
    token_response.__aexit__ = AsyncMock(return_value=None)

    # Mock first put response (401 Unauthorized)
    error_response = AsyncMock()
    error_response.status = 401
    error_response.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=401,
            message="Unauthorized",
            headers={}
        )
    )
    error_response.__aenter__ = AsyncMock(return_value=error_response)
    error_response.__aexit__ = AsyncMock(return_value=None)

    # Mock second put response (success after token refresh)
    success_response = AsyncMock()
    success_response.status = 200
    success_response.raise_for_status = MagicMock()
    success_response.__aenter__ = AsyncMock(return_value=success_response)
    success_response.__aexit__ = AsyncMock(return_value=None)

    # Setup mocks
    mock_session.post = MagicMock(return_value=token_response)
    mock_session.put = MagicMock(side_effect=[error_response, success_response])

    result = await client.set_resource("/zones/zn1/temperatureHeatingSetpoint", 21.5)

    assert result is True
    # Verify token was refreshed
    assert client._access_token == "new_access_token"
    # Verify put was called twice (first 401, then retry after refresh)
    assert mock_session.put.call_count == 2
    # Verify post was called once (token refresh)
    assert mock_session.post.call_count == 1


@pytest.mark.asyncio
async def test_get_gateways(mock_session):
    """Test listing available gateways."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="valid_token",
        refresh_token="refresh_token_123"
    )

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[
        {"deviceId": "101270435", "deviceType": "rrc2"},
        {"deviceId": "987654321", "deviceType": "rrc2"}
    ])
    mock_response.raise_for_status = MagicMock()

    mock_session.get = MagicMock(return_value=mock_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    gateways = await client.get_gateways()

    assert len(gateways) == 2
    assert gateways[0]["deviceId"] == "101270435"


@pytest.mark.asyncio
async def test_get_device_info(mock_session):
    """Test getting device information."""
    client = PointTRestClient(
        session=mock_session,
        device_id="101270435",
        access_token="valid_token",
        refresh_token="refresh_token_123"
    )

    # Mock multiple resource calls
    uuid_response = {"id": "/gateway/uuid", "value": "101270435"}
    firmware_response = {"id": "/gateway/versionFirmware", "value": "05.04.00"}
    product_response = {"id": "/gateway/productID", "value": "8737906739"}

    mock_session.get = AsyncMock()

    async def mock_get_resource(path):
        """Mock get_resource based on path."""
        if "uuid" in path:
            return uuid_response
        elif "versionFirmware" in path:
            return firmware_response
        elif "productID" in path:
            return product_response
        return None

    client.get_resource = AsyncMock(side_effect=mock_get_resource)

    device_info = await client.get_device_info()

    assert device_info["uuid"] == "101270435"
    assert device_info["firmware"] == "05.04.00"
    assert device_info["product_id"] == "8737906739"
