"""Tests for the CT200 REST gateway wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import importlib.util
from pathlib import Path
import sys

# Mock the dependencies before loading the module
mock_config_entries = MagicMock()
mock_pointt_rest_client = MagicMock()
mock_const = MagicMock()
mock_const.DEVICE_ID = "device_id"
mock_const.UUID = "uuid"
mock_rest_zone = MagicMock()
mock_rest_heating_circuit = MagicMock()
mock_rest_dhw_circuit = MagicMock()

sys.modules['homeassistant.config_entries'] = mock_config_entries
sys.modules['custom_components.bosch.pointt_rest_client'] = mock_pointt_rest_client
sys.modules['custom_components.bosch.const'] = mock_const
sys.modules['custom_components.bosch.rest_zone'] = mock_rest_zone
sys.modules['custom_components.bosch.rest_heating_circuit'] = mock_rest_heating_circuit
sys.modules['custom_components.bosch.rest_dhw_circuit'] = mock_rest_dhw_circuit

# Now load the module
rest_gateway_wrapper_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "rest_gateway_wrapper.py"
spec = importlib.util.spec_from_file_location(
    "custom_components.bosch.rest_gateway_wrapper",
    rest_gateway_wrapper_path,
)
rest_gateway_wrapper = importlib.util.module_from_spec(spec)

# Inject the mocked modules into the wrapper's namespace
rest_gateway_wrapper.PointTRestClient = MagicMock()
rest_gateway_wrapper.ConfigEntry = MagicMock()
rest_gateway_wrapper.DEVICE_ID = "device_id"
rest_gateway_wrapper.UUID = "uuid"

spec.loader.exec_module(rest_gateway_wrapper)

RestGatewayWrapper = rest_gateway_wrapper.RestGatewayWrapper


def _make_async_zone_mock():
    """Create a mock that mimics a RestZone / RestHeatingCircuit / RestDhwCircuit."""
    zone = MagicMock()
    zone.initialize = AsyncMock(return_value=True)
    zone.update = AsyncMock()
    return zone


# Configure the module-level mocks so that constructing zone/circuit objects
# returns proper async-capable mocks.
mock_rest_zone.RestZone.return_value = _make_async_zone_mock()
mock_rest_heating_circuit.RestHeatingCircuit.return_value = _make_async_zone_mock()
mock_rest_dhw_circuit.RestDhwCircuit.return_value = _make_async_zone_mock()


@pytest.fixture
def mock_client():
    """Create a mock PointTRestClient."""
    client = MagicMock()
    client.device_id = "101270435"
    return client


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = {
        "device_id": "101270435",
        "uuid": "101270435",
        "access_token": "token",
        "refresh_token": "refresh",
    }
    return entry


def test_wrapper_initialization(mock_client, mock_entry):
    """Test gateway wrapper initializes correctly."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    assert wrapper.client == mock_client
    assert wrapper.entry == mock_entry
    assert wrapper.uuid == "101270435"
    assert wrapper.device_id == "101270435"


def test_wrapper_properties(mock_client, mock_entry):
    """Test wrapper exposes correct properties."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    # Should have basic gateway properties
    assert hasattr(wrapper, 'uuid')
    assert hasattr(wrapper, 'device_id')
    assert hasattr(wrapper, 'client')

    # Should have circuit storage
    assert hasattr(wrapper, '_zones')
    assert hasattr(wrapper, '_resource_cache')


def test_wrapper_missing_uuid(mock_client, mock_entry):
    """Test wrapper raises ValueError when uuid is missing."""
    mock_entry.data = {
        "device_id": "101270435",
        "access_token": "token",
        "refresh_token": "refresh",
    }

    with pytest.raises(ValueError, match="Invalid config entry: missing uuid or device_id"):
        RestGatewayWrapper(client=mock_client, entry=mock_entry)


def test_wrapper_missing_device_id(mock_client, mock_entry):
    """Test wrapper raises ValueError when device_id is missing."""
    mock_entry.data = {
        "uuid": "101270435",
        "access_token": "token",
        "refresh_token": "refresh",
    }

    with pytest.raises(ValueError, match="Invalid config entry: missing uuid or device_id"):
        RestGatewayWrapper(client=mock_client, entry=mock_entry)


@pytest.mark.asyncio
async def test_wrapper_initialize(mock_client, mock_entry):
    """Test wrapper initialization fetches device data."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    # Mock device info call
    mock_client.get_device_info = AsyncMock(return_value={
        "uuid": "101270435",
        "firmware": "05.04.00",
        "product_id": "8737906739"
    })

    result = await wrapper.initialize()

    mock_client.get_device_info.assert_called_once()
    assert result is True
    assert wrapper.device_name == "Bosch CT200 (101270435)"
    assert wrapper.firmware == "05.04.00"
    assert wrapper.product_id == "8737906739"


@pytest.mark.asyncio
async def test_wrapper_update(mock_client, mock_entry):
    """Test wrapper update calls zone, HC, DHW, and system cache updates."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    # Add mock zone, HC, and DHW so update() calls their update() methods
    mock_zone = MagicMock()
    mock_zone.update = AsyncMock()
    wrapper._zones["zn1"] = mock_zone

    mock_hc = MagicMock()
    mock_hc.update = AsyncMock()
    wrapper._rest_heating_circuits.append(mock_hc)

    mock_dhw = MagicMock()
    mock_dhw.update = AsyncMock()
    wrapper._dhw_circuits.append(mock_dhw)

    mock_client.post_bulk_resources = AsyncMock(
        return_value=[
            {
                "gatewayId": "101270435",
                "resourcePaths": [
                    {
                        "resourcePath": path,
                        "serverStatus": 200,
                        "gatewayResponse": {
                            "status": 200,
                            "payload": {"id": path, "value": f"bulk:{path}", "type": "string"},
                        },
                    }
                    for path in RestGatewayWrapper.BULK_PRIMARY_ENDPOINTS
                ],
            }
        ]
    )
    mock_client.get_resource = AsyncMock(return_value={"value": "test", "type": "string"})

    await wrapper.update()

    # Zone, HC, and DHW updates should be called
    mock_zone.update.assert_called_once()
    mock_hc.update.assert_called_once()
    mock_dhw.update.assert_called_once()

    cache = wrapper.system_cache
    assert isinstance(cache, dict), "system_cache must be a dict"
    for endpoint in RestGatewayWrapper.SYSTEM_ENDPOINTS:
        assert endpoint in cache, f"Missing endpoint in cache: {endpoint}"


@pytest.mark.asyncio
async def test_wrapper_update_does_not_fallback_to_leaf_reads(mock_client, mock_entry):
    """Bulk failures should not trigger per-path leaf reads during updates."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    bulk_success_path = "/zones/zn1/temperatureActual"
    bulk_failed_path = "/system/sensors/temperatures/outdoor_t1"

    mock_client.post_bulk_resources = AsyncMock(
        return_value=[
            {
                "gatewayId": "101270435",
                "resourcePaths": [
                    {
                        "resourcePath": bulk_success_path,
                        "serverStatus": 200,
                        "gatewayResponse": {
                            "status": 200,
                            "payload": {"id": bulk_success_path, "value": 21.5},
                        },
                    },
                    {
                        "resourcePath": bulk_failed_path,
                        "serverStatus": 504,
                        "gatewayResponse": None,
                    },
                ],
            }
        ]
    )

    async def get_resource_side_effect(path):
        return {"id": path, "value": f"fallback:{path}"}

    mock_client.get_resource = AsyncMock(side_effect=get_resource_side_effect)

    await wrapper.update()

    assert wrapper.get_cached_resource(bulk_success_path) == {
        "id": bulk_success_path,
        "value": 21.5,
    }
    assert wrapper.get_cached_resource(bulk_failed_path) is None
    mock_client.get_resource.assert_not_called()


@pytest.mark.asyncio
async def test_wrapper_retries_whole_bulk_request_once(mock_client, mock_entry):
    """Transient bulk errors should trigger a single retry of the whole request."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    mock_client.post_bulk_resources = AsyncMock(
        side_effect=[
            Exception("temporary bulk failure"),
            [
                {
                    "gatewayId": "101270435",
                    "resourcePaths": [
                        {
                            "resourcePath": "/zones/zn1/temperatureActual",
                            "serverStatus": 200,
                            "gatewayResponse": {
                                "status": 200,
                                "payload": {
                                    "id": "/zones/zn1/temperatureActual",
                                    "value": 22.0,
                                },
                            },
                        }
                    ],
                }
            ],
        ]
    )
    mock_client.get_resource = AsyncMock(return_value=None)

    await wrapper.update()

    assert mock_client.post_bulk_resources.await_count == 2
    assert wrapper.get_cached_resource("/zones/zn1/temperatureActual") == {
        "id": "/zones/zn1/temperatureActual",
        "value": 22.0,
    }
    mock_client.get_resource.assert_not_called()


@pytest.mark.asyncio
async def test_wrapper_blacklists_forbidden_bulk_paths(mock_client, mock_entry):
    """Forbidden bulk paths should be skipped in later bulk requests."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    forbidden_path = "/zones/zn1/testForbidden"
    wrapper._bulk_blacklist.discard(forbidden_path)
    wrapper.BULK_PRIMARY_ENDPOINTS = [forbidden_path]

    mock_client.post_bulk_resources = AsyncMock(
        side_effect=[
            [
                {
                    "gatewayId": "101270435",
                    "resourcePaths": [
                        {
                            "resourcePath": forbidden_path,
                            "serverStatus": 403,
                            "gatewayResponse": None,
                        }
                    ],
                }
            ],
            [],
        ]
    )
    mock_client.get_resource = AsyncMock(return_value=None)

    await wrapper.update()
    assert forbidden_path in wrapper.bulk_blacklist

    await wrapper.update()

    first_call = mock_client.post_bulk_resources.await_args_list[0].args[0]
    assert forbidden_path in first_call
    assert mock_client.post_bulk_resources.await_count == 1


@pytest.mark.asyncio
async def test_wrapper_initialize_failure(mock_client, mock_entry):
    """Test wrapper initialization handles errors gracefully."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    mock_client.get_device_info = AsyncMock(side_effect=Exception("Connection failed"))

    result = await wrapper.initialize()

    assert result is False


@pytest.mark.asyncio
async def test_wrapper_update_raises_on_error(mock_client, mock_entry):
    """Test wrapper update re-raises exceptions."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    # Add a mock zone that raises so update() re-raises
    mock_zone = MagicMock()
    mock_zone.update = AsyncMock(side_effect=Exception("API error"))
    wrapper._zones["zn1"] = mock_zone

    with pytest.raises(Exception, match="API error"):
        await wrapper.update()


# ---------------------------------------------------------------------------
# New tests for system cache (Task 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_populates_system_cache(mock_client, mock_entry):
    """All 16 system endpoints are cached after update()."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    mock_client.post_bulk_resources = AsyncMock(
        return_value=[
            {
                "gatewayId": "101270435",
                "resourcePaths": [
                    {
                        "resourcePath": path,
                        "serverStatus": 200,
                        "gatewayResponse": {
                            "status": 200,
                            "payload": {"id": path, "value": f"mocked:{path}", "type": "string"},
                        },
                    }
                    for path in RestGatewayWrapper.SYSTEM_ENDPOINTS
                ],
            }
        ]
    )
    mock_client.get_resource = AsyncMock(return_value=None)

    await wrapper.update()

    # system_cache property must exist and contain all 16 endpoints
    cache = wrapper.system_cache
    assert isinstance(cache, dict), "system_cache must be a dict"
    assert len(cache) == 16, f"Expected 16 entries, got {len(cache)}"

    for endpoint in RestGatewayWrapper.SYSTEM_ENDPOINTS:
        assert endpoint in cache, f"Missing endpoint in cache: {endpoint}"
        assert cache[endpoint] is not None, f"Endpoint {endpoint} should not be None"
        assert cache[endpoint]["value"] == f"mocked:{endpoint}"


@pytest.mark.asyncio
async def test_update_system_cache_survives_single_endpoint_failure(mock_client, mock_entry):
    """When one bulk system endpoint fails, the rest are still cached."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    failing_endpoint = "/gateway/pirSensitivity"

    mock_client.post_bulk_resources = AsyncMock(
        return_value=[
            {
                "gatewayId": "101270435",
                "resourcePaths": [
                    {
                        "resourcePath": path,
                        "serverStatus": 504 if path == failing_endpoint else 200,
                        "gatewayResponse": None if path == failing_endpoint else {
                            "status": 200,
                            "payload": {"id": path, "value": f"mocked:{path}", "type": "string"},
                        },
                    }
                    for path in RestGatewayWrapper.SYSTEM_ENDPOINTS
                ],
            }
        ]
    )
    mock_client.get_resource = AsyncMock(return_value=None)

    await wrapper.update()

    cache = wrapper.system_cache
    assert isinstance(cache, dict)

    other_endpoints = [ep for ep in RestGatewayWrapper.SYSTEM_ENDPOINTS if ep != failing_endpoint]
    for endpoint in other_endpoints:
        assert endpoint in cache, f"Missing endpoint in cache: {endpoint}"
        assert cache[endpoint] is not None, f"Endpoint {endpoint} should not be None"
    assert failing_endpoint not in cache


@pytest.mark.asyncio
async def test_update_system_cache_handles_exception(mock_client, mock_entry):
    """Bulk exceptions leave cache empty and do not trigger leaf reads."""
    wrapper = RestGatewayWrapper(client=mock_client, entry=mock_entry)

    mock_client.post_bulk_resources = AsyncMock(side_effect=Exception("Simulated network error"))
    mock_client.get_resource = AsyncMock(return_value={"value": "unexpected"})

    await wrapper.update()

    cache = wrapper.system_cache
    assert isinstance(cache, dict)
    assert cache == {}
    mock_client.get_resource.assert_not_called()
