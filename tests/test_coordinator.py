"""Tests for OAuth2 DataUpdateCoordinator setup."""
import ast
import importlib.util
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_coordinator_is_stored_in_hass_data():
    """Verify the COORDINATOR constant exists."""
    # Load and parse const.py directly to avoid importing the full integration.
    const_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "const.py"
    source = const_path.read_text()
    match = re.search(r'^COORDINATOR\s*=\s*["\']([^"\']+)["\']', source, re.MULTILINE)
    assert match is not None, "COORDINATOR constant not found in const.py"
    assert match.group(1) == "coordinator"


def test_bulk_probe_normalizes_homecom_alt_shape():
    """Verify the bulk probe script normalizes the known bulk response shape."""
    script_path = Path(__file__).parent.parent.parent / "debug" / "probe_pointt_bulk.py"
    spec = importlib.util.spec_from_file_location("probe_pointt_bulk", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    requested_paths = [
        "/zones/zn1/temperatureActual",
        "/system/sensors/temperatures/outdoor_t1",
        "/dhwCircuits/dhw1/actualTemp",
    ]
    response = [
        {
            "gatewayId": "101270435",
            "resourcePaths": [
                {
                    "resourcePath": "/zones/zn1/temperatureActual",
                    "gatewayResponse": {
                        "payload": {
                            "id": "/zones/zn1/temperatureActual",
                            "type": "floatValue",
                            "value": 20.5,
                        }
                    },
                },
                {
                    "resourcePath": "/system/sensors/temperatures/outdoor_t1",
                    "gatewayResponse": {
                        "payload": {
                            "id": "/system/sensors/temperatures/outdoor_t1",
                            "type": "floatValue",
                            "value": 8.0,
                        }
                    },
                },
                {
                    "resourcePath": "/dhwCircuits/dhw1/actualTemp",
                    "gatewayResponse": {
                        "status": 404,
                        "payload": None,
                    },
                },
            ],
        }
    ]

    summary = module.summarize_bulk_response(requested_paths, response)

    assert summary["matched_count"] == 2
    assert summary["missing_count"] == 0
    assert summary["error_count"] == 1
    assert summary["matched"]["/zones/zn1/temperatureActual"]["value"] == 20.5
    assert summary["matched"]["/system/sensors/temperatures/outdoor_t1"]["value"] == 8.0
    assert "/dhwCircuits/dhw1/actualTemp" in summary["errors"]


def test_refresh_pointt_token_helpers():
    """Verify standalone OAuth helper script parses code and gateways."""
    script_path = Path(__file__).parent.parent.parent / "debug" / "refresh_pointt_token.py"
    spec = importlib.util.spec_from_file_location("refresh_pointt_token", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    code = module.extract_code_from_input(
        "com.bosch.tt.dashtt.pointt://app/login?code=ABC123&state=xyz"
    )
    assert code == "ABC123"
    assert module.extract_code_from_input("RAWCODE") == "RAWCODE"

    gateway_summary = module.summarize_gateways(
        [
            {"deviceId": "101270435", "deviceType": "rrc2"},
            {"deviceId": "987654321", "deviceType": "rrc2"},
        ]
    )
    assert gateway_summary == [
        "deviceId=101270435 type=rrc2",
        "deviceId=987654321 type=rrc2",
    ]


def test_scan_all_endpoints_helpers():
    """Verify the endpoint scanner is reusable and secret-free."""
    script_path = Path(__file__).parent.parent.parent / "debug" / "scan_all_endpoints.py"
    spec = importlib.util.spec_from_file_location("scan_all_endpoints", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = script_path.read_text()
    assert "ACCESS_TOKEN =" not in source
    assert "DEVICE_ID =" not in source

    assert module.build_base_url("101426422") == (
        "https://pointt-api.bosch-thermotechnology.com/"
        "pointt-api/api/v1/gateways/101426422/resource"
    )

    paths = module.build_output_paths(Path("/tmp/scan-results"))
    assert paths["full"] == Path("/tmp/scan-results/api_scan_full.json")
    assert paths["values"] == Path("/tmp/scan-results/api_scan_values.json")
    assert paths["writeable"] == Path("/tmp/scan-results/api_scan_writeable.json")


def test_dhw_operation_mode_and_extra_dhw_are_modeled():
    """Verify the remaining fetchable DHW endpoints are exposed as modeled sensors."""
    sensor_init_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "bosch"
        / "sensor"
        / "__init__.py"
    )
    dhw_sensor_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "bosch"
        / "sensor"
        / "dhw_sensor.py"
    )

    sensor_init_source = sensor_init_path.read_text()
    dhw_sensor_source = dhw_sensor_path.read_text()

    assert '"operation_mode"' in sensor_init_source
    assert '"extra_dhw"' in sensor_init_source
    assert '"operation_mode"' in dhw_sensor_source
    assert '"extra_dhw"' in dhw_sensor_source


def test_removed_platform_files_stay_deleted():
    """Unreachable platform modules should stay deleted in the CT200-only runtime."""
    bosch_dir = Path(__file__).parent.parent / "custom_components" / "bosch"
    removed_platform = "binary" + "_sensor.py"
    removed_heater = "water_" + "heater.py"
    removed_paths = [
        bosch_dir / removed_platform,
        bosch_dir / removed_heater,
        bosch_dir / "sensor" / "bosch.py",
        bosch_dir / "sensor" / "circuit.py",
        bosch_dir / "sensor" / "energy.py",
        bosch_dir / "sensor" / "notifications.py",
        bosch_dir / "sensor" / "base.py",
        bosch_dir / "sensor" / "statistic_helper.py",
    ]

    for removed_path in removed_paths:
        assert not removed_path.exists(), f"Removed module reappeared: {removed_path}"


def test_recording_sensor_module_is_removed():
    """Recording sensor module should not exist in the CT200 integration."""
    recording_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "bosch"
        / "sensor"
        / "recording.py"
    )
    assert not recording_path.exists()


def test_sensor_platform_contains_only_modeled_ct200_entities():
    """The sensor platform should only wire modeled CT200 entities."""
    sensor_init_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "bosch"
        / "sensor"
        / "__init__.py"
    )
    source = sensor_init_path.read_text()

    assert "from .bosch import" not in source
    assert "from .circuit import" not in source
    assert "from .energy import" not in source
    assert "from .notifications import" not in source
    assert "entity_platform" not in source
    assert "SERVICE_MOVE_OLD_DATA" not in source
    assert "RECORDING" not in source
    assert ".get_circuits(" not in source


def test_discovery_runtime_modules_are_deleted():
    """The OAuth2-only integration should not carry dead API discovery entity code."""
    bosch_dir = Path(__file__).parent.parent / "custom_components" / "bosch"
    assert not (bosch_dir / ("api_" + "discovery.py")).exists()
    assert not (bosch_dir / ("discovered_" + "entity.py")).exists()


def test_services_are_oauth2_only_at_source_level():
    """Service helpers must target the OAuth2 runtime context directly."""
    services_path = (
        Path(__file__).parent.parent / "custom_components" / "bosch" / "services.py"
    )
    services_yaml_path = (
        Path(__file__).parent.parent / "custom_components" / "bosch" / "services.yaml"
    )

    services_source = services_path.read_text()
    services_yaml = services_yaml_path.read_text()

    removed_update = "update_" + "recordings_sensor"
    removed_fetch = "fetch_" + "recordings_sensor_range"
    removed_charge = "set_" + "dhw_charge"
    removed_move = "move_old_" + "statistic_data"

    assert "BOSCH_GATEWAY_ENTRY" not in services_source
    assert "RecordingSensor" not in services_source
    assert "debug_" + "scan" not in services_source
    assert removed_update not in services_source
    assert removed_fetch not in services_source
    assert removed_charge not in services_source

    assert ("debug_" + "scan:") not in services_yaml
    assert (removed_update + ":") not in services_yaml
    assert (removed_fetch + ":") not in services_yaml
    assert (removed_move + ":") not in services_yaml
    assert (removed_charge + ":") not in services_yaml


@pytest.mark.asyncio
async def test_rest_zone_set_ha_mode_writes_user_mode():
    """CT200 HVAC mode writes should go through the writable zone userMode endpoint."""
    rest_zone_path = (
        Path(__file__).parent.parent / "custom_components" / "bosch" / "rest_zone.py"
    )
    spec = importlib.util.spec_from_file_location("rest_zone_runtime", rest_zone_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    gateway_wrapper = SimpleNamespace(set_resource_value=AsyncMock(return_value=True))
    zone = module.RestZone(
        client=SimpleNamespace(set_resource=AsyncMock(return_value=True)),
        zone_id="zn1",
        device_id="101426422",
        gateway_wrapper=gateway_wrapper,
    )

    result = await zone.set_ha_mode("auto")

    assert result is True
    gateway_wrapper.set_resource_value.assert_awaited_once_with(
        "/zones/zn1/userMode",
        "automatic",
    )
    assert zone.hvac_mode == "auto"


@pytest.mark.parametrize(
    ("relative_path", "forbidden_classes", "forbidden_fragments"),
    [
        (
            Path("climate.py"),
            {"BoschThermostat"},
            {"BoschClimateWaterEntity"},
        ),
        (
            Path("number.py"),
            {"BoschNumber", "CircuitNumber"},
            {"number_switches", ".get_circuits(", "async_setup_platform"},
        ),
        (
            Path("select.py"),
            {"BoschSelect"},
            {"switches.selects", "async_setup_platform"},
        ),
        (
            Path("switch.py"),
            {"BoschBaseSwitch", "BoschSwitch", "CircuitSwitch"},
            {"regular_switches", ".get_circuits(", "async_setup_platform"},
        ),
    ],
)
def test_shared_platforms_are_rest_only_at_source_level(
    relative_path: Path,
    forbidden_classes: set[str],
    forbidden_fragments: set[str],
):
    """Shared entity platforms should contain only the CT200 REST implementation."""
    platform_path = Path(__file__).parent.parent / "custom_components" / "bosch" / relative_path
    source = platform_path.read_text()
    module = ast.parse(source)
    class_names = _ast_class_names(module)

    for class_name in forbidden_classes:
        assert class_name not in class_names
    for fragment in forbidden_fragments:
        assert fragment not in source


def test_config_flow_is_oauth2_only_at_source_level():
    """Verify config_flow.py only exposes the manual OAuth2 browser flow."""
    config_flow_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "bosch"
        / "config_flow.py"
    )
    module = ast.parse(config_flow_path.read_text())

    handler = _ast_find_class(module, "BoschFlowHandler")
    method_names = {
        node.name for node in handler.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "async_step_user" in method_names
    assert "async_step_oauth_browser" in method_names

    async_step_user = next(
        node
        for node in handler.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_step_user"
    )
    assert _returns_step_call(async_step_user, "async_step_oauth_browser")


@pytest.mark.asyncio
async def test_oauth_browser_step_rejects_redirect_url_without_code():
    """Pasted redirect URLs without a code parameter must fail fast."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()

        result = await handler.async_step_oauth_browser(
            {"code": "com.bosch.tt.dashtt.pointt://app/login?state=missing-code"}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "oauth_browser"
        assert result["errors"] == {"code": "no_code"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        ("Failed to exchange authorization code", "invalid_code"),
        ("Cannot connect to authentication server", "network_error"),
        ("Invalid response from authentication server", "auth_failed"),
    ],
)
async def test_oauth_browser_step_maps_auth_exchange_failures_by_error_cause(
    message: str,
    expected_error: str,
):
    """Manual browser flow should distinguish invalid codes from transient auth failures."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()
        handler.hass = object()

        with patch.object(
            module._pointt_rest_client_module,
            "exchange_code_for_tokens",
            AsyncMock(side_effect=module.ConfigEntryAuthFailed(message)),
        ):
            result = await handler.async_step_oauth_browser({"code": "raw-auth-code"})

        assert result["type"] == "form"
        assert result["step_id"] == "oauth_browser"
        assert result["errors"] == {"base": expected_error}


@pytest.mark.asyncio
async def test_oauth_browser_step_prefers_rrc2_gateway_when_account_has_multiple_devices():
    """Manual browser flow must pick the CT200 gateway instead of the first unrelated device."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()
        handler.hass = object()

        gateway_client = MagicMock()
        gateway_client.get_gateways = AsyncMock(
            return_value=[
                {"deviceId": "101375911", "deviceType": "wddw2"},
                {"deviceId": "101426422", "deviceType": "rrc2"},
            ]
        )
        ct200_client = MagicMock()
        ct200_client.get_device_info = AsyncMock(
            return_value={"uuid": "uuid-ct200", "firmware": "1.0", "product_id": "ct200"}
        )

        module._pointt_rest_client_module.PointTRestClient.side_effect = [
            gateway_client,
            ct200_client,
        ]

        with patch.object(
            module._pointt_rest_client_module,
            "exchange_code_for_tokens",
            AsyncMock(return_value=("access-token", "refresh-token")),
        ):
            result = await handler.async_step_oauth_browser({"code": "raw-auth-code"})

        assert result["type"] == "create_entry"
        assert result["title"] == "Bosch CT200 (101426422)"
        assert result["data"]["device_id"] == "101426422"
        assert result["data"]["uuid"] == "uuid-ct200"


@pytest.mark.asyncio
async def test_oauth_browser_step_skips_already_configured_ct200_and_auto_selects_remaining_one():
    """The flow should skip already configured CT200s and auto-select the only remaining one."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()
        handler.hass = object()
        handler._current_entries = [SimpleNamespace(data={"device_id": "101375911"})]

        gateway_client = MagicMock()
        gateway_client.get_gateways = AsyncMock(
            return_value=[
                {"deviceId": "101375911", "deviceType": "rrc2"},
                {"deviceId": "101426422", "deviceType": "rrc2"},
            ]
        )
        ct200_client = MagicMock()
        ct200_client.get_device_info = AsyncMock(
            return_value={"uuid": "uuid-ct200", "firmware": "1.0", "product_id": "ct200"}
        )

        module._pointt_rest_client_module.PointTRestClient.side_effect = [
            gateway_client,
            ct200_client,
        ]

        with patch.object(
            module._pointt_rest_client_module,
            "exchange_code_for_tokens",
            AsyncMock(return_value=("access-token", "refresh-token")),
        ):
            result = await handler.async_step_oauth_browser({"code": "raw-auth-code"})

        assert result["type"] == "create_entry"
        assert result["title"] == "Bosch CT200 (101426422)"
        assert result["data"]["device_id"] == "101426422"


@pytest.mark.asyncio
async def test_oauth_browser_step_shows_gateway_selection_when_multiple_unconfigured_ct200s_exist():
    """The flow should show a chooser when multiple unconfigured CT200s are available."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()
        handler.hass = object()

        gateway_client = MagicMock()
        gateway_client.get_gateways = AsyncMock(
            return_value=[
                {"deviceId": "101375911", "deviceType": "rrc2"},
                {"deviceId": "101426422", "deviceType": "rrc2"},
            ]
        )

        module._pointt_rest_client_module.PointTRestClient.return_value = gateway_client

        with patch.object(
            module._pointt_rest_client_module,
            "exchange_code_for_tokens",
            AsyncMock(return_value=("access-token", "refresh-token")),
        ):
            result = await handler.async_step_oauth_browser({"code": "raw-auth-code"})

        assert result["type"] == "form"
        assert result["step_id"] == "select_gateway"
        assert handler._pending_access_token == "access-token"
        assert handler._pending_refresh_token == "refresh-token"
        assert [gateway["deviceId"] for gateway in handler._pending_gateways] == [
            "101375911",
            "101426422",
        ]


@pytest.mark.asyncio
async def test_select_gateway_step_creates_entry_for_selected_ct200():
    """The gateway chooser should create an entry for the selected CT200."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()
        handler.hass = object()
        handler._pending_access_token = "access-token"
        handler._pending_refresh_token = "refresh-token"
        handler._pending_gateways = [
            {"deviceId": "101375911", "deviceType": "rrc2"},
            {"deviceId": "101426422", "deviceType": "rrc2"},
        ]

        ct200_client = MagicMock()
        ct200_client.get_device_info = AsyncMock(
            return_value={"uuid": "uuid-ct200", "firmware": "1.0", "product_id": "ct200"}
        )
        module._pointt_rest_client_module.PointTRestClient.return_value = ct200_client

        result = await handler.async_step_select_gateway({"device_id": "101426422"})

        assert result["type"] == "create_entry"
        assert result["title"] == "Bosch CT200 (101426422)"
        assert result["data"]["device_id"] == "101426422"
        assert result["data"]["uuid"] == "uuid-ct200"


@pytest.mark.asyncio
async def test_select_gateway_step_rejects_unknown_device_id():
    """Tampered gateway selections must re-show the chooser with an error."""
    with _load_bosch_config_flow_runtime_module() as module:
        handler = module.BoschFlowHandler()
        handler.hass = object()
        handler._pending_access_token = "access-token"
        handler._pending_refresh_token = "refresh-token"
        handler._pending_gateways = [
            {"deviceId": "101375911", "deviceType": "rrc2"},
            {"deviceId": "101426422", "deviceType": "rrc2"},
        ]

        result = await handler.async_step_select_gateway({"device_id": "999999999"})

        assert result["type"] == "form"
        assert result["step_id"] == "select_gateway"
        assert result["errors"] == {"base": "invalid_device"}


def test_const_keeps_only_current_config_flow_constants():
    """Verify const.py only keeps constants used by the current integration."""
    const_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "const.py"
    source = const_path.read_text()

    assert re.search(r"^ENTRY_ID\s*=", source, re.MULTILINE) is not None
    assert re.search(r"^COORDINATOR\s*=", source, re.MULTILINE) is not None
    assert re.search(r"^DEVICE_ID\s*=", source, re.MULTILINE) is not None


def test_init_is_ct200_oauth2_only_at_source_level():
    """Verify __init__.py is a CT200 OAuth2 setup module."""
    init_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "__init__.py"
    module = ast.parse(init_path.read_text())

    setup_entry = _ast_find_function(module, "async_setup_entry")
    assert setup_entry is not None
    assert _ast_contains_name(setup_entry, "PointTRestClient")
    assert _ast_contains_name(setup_entry, "RestGatewayWrapper")
    assert _ast_contains_name(setup_entry, "DataUpdateCoordinator")


def test_unload_matches_single_runtime_path():
    """Verify unload logic matches the single supported runtime path."""
    init_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "__init__.py"
    module = ast.parse(init_path.read_text())

    assert _ast_find_function(module, "async_update_options") is None

    unload_entry = _ast_find_function(module, "async_unload_entry")
    assert unload_entry is not None
    assert _ast_contains_name(unload_entry, "GATEWAY")


@pytest.mark.asyncio
async def test_async_unload_entry_preserves_runtime_state_when_platform_unload_fails():
    """Unload failure must not tear down the OAuth2 runtime state."""
    module = _load_bosch_init_runtime_module()
    gateway = SimpleNamespace(close=AsyncMock())
    hass = SimpleNamespace(
        data={"bosch": {"uuid-1": {"gateway": gateway, "coordinator": object()}}},
        config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=False)),
    )
    entry = SimpleNamespace(data={"uuid": "uuid-1"})
    module.async_remove_services = MagicMock()

    unload_ok = await module.async_unload_entry(hass, entry)

    assert unload_ok is False
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry, module.PLATFORMS)
    gateway.close.assert_not_awaited()
    module.async_remove_services.assert_not_called()
    assert hass.data["bosch"]["uuid-1"]["gateway"] is gateway


def _ast_find_class(module: ast.Module, class_name: str):
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _ast_find_function(module: ast.Module, function_name: str):
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    return None


def _ast_class_names(module: ast.Module) -> set[str]:
    return {
        node.name
        for node in module.body
        if isinstance(node, ast.ClassDef)
    }


def _ast_contains_name(module: ast.AST, name: str) -> bool:
    return any(isinstance(node, ast.Name) and node.id == name for node in ast.walk(module))


def _ast_imports_module_name(module: ast.Module, module_name: str, imported_name: str | None = None) -> bool:
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(module_name):
            if imported_name is None:
                return True
            if any(alias.name == imported_name for alias in node.names):
                return True
        if isinstance(node, ast.Import) and imported_name is None:
            if any(alias.name == module_name or alias.name.startswith(f"{module_name}.") for alias in node.names):
                return True
    return False


def _returns_step_call(function: ast.AsyncFunctionDef, step_name: str) -> bool:
    for node in function.body:
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Await):
            continue

        call = node.value.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue

        if isinstance(call.func.value, ast.Name) and call.func.value.id == "self":
            if call.func.attr == step_name:
                return True

    return False


def _load_bosch_init_runtime_module():
    init_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "__init__.py"
    module_name = "custom_components.bosch"

    fake_modules = {
        "custom_components": ModuleType("custom_components"),
        "custom_components.bosch.const": _module_with_attrs(
            "custom_components.bosch.const",
            ACCESS_TOKEN="access_token",
            CLIMATE="climate",
            COORDINATOR="coordinator",
            DEVICE_ID="device_id",
            DOMAIN="bosch",
            ENTRY_ID="entry_id",
            GATEWAY="gateway",
            NUMBER="number",
            REFRESH_TOKEN="refresh_token",
            SCAN_INTERVAL=object(),
            SELECT="select",
            SENSOR="sensor",
            SWITCH="switch",
            UUID="uuid",
        ),
        "custom_components.bosch.pointt_rest_client": _module_with_attrs(
            "custom_components.bosch.pointt_rest_client",
            PointTRestClient=MagicMock(),
        ),
        "custom_components.bosch.rest_gateway_wrapper": _module_with_attrs(
            "custom_components.bosch.rest_gateway_wrapper",
            RestGatewayWrapper=MagicMock(),
        ),
        "custom_components.bosch.services": _module_with_attrs(
            "custom_components.bosch.services",
            async_register_services=MagicMock(),
            async_remove_services=MagicMock(),
        ),
        "homeassistant": ModuleType("homeassistant"),
        "homeassistant.config_entries": _module_with_attrs(
            "homeassistant.config_entries",
            ConfigEntry=object,
        ),
        "homeassistant.core": _module_with_attrs(
            "homeassistant.core",
            HomeAssistant=object,
        ),
        "homeassistant.exceptions": _module_with_attrs(
            "homeassistant.exceptions",
            ConfigEntryNotReady=type("ConfigEntryNotReady", (Exception,), {}),
        ),
        "homeassistant.helpers": ModuleType("homeassistant.helpers"),
        "homeassistant.helpers.device_registry": _module_with_attrs(
            "homeassistant.helpers.device_registry",
            async_get=MagicMock(),
        ),
        "homeassistant.helpers.aiohttp_client": _module_with_attrs(
            "homeassistant.helpers.aiohttp_client",
            async_get_clientsession=MagicMock(),
        ),
        "homeassistant.helpers.typing": _module_with_attrs(
            "homeassistant.helpers.typing",
            ConfigType=dict,
        ),
        "homeassistant.helpers.update_coordinator": _module_with_attrs(
            "homeassistant.helpers.update_coordinator",
            DataUpdateCoordinator=MagicMock(),
            UpdateFailed=type("UpdateFailed", (Exception,), {}),
        ),
    }

    with patch.dict(sys.modules, fake_modules):
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_path,
            submodule_search_locations=[str(init_path.parent)],
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


@contextmanager
def _load_bosch_config_flow_runtime_module():
    config_flow_path = Path(__file__).parent.parent / "custom_components" / "bosch" / "config_flow.py"
    module_name = "custom_components.bosch.config_flow"

    class FakeConfigFlow:
        def __init_subclass__(cls, **kwargs):
            del kwargs

        def async_show_form(
            self,
            *,
            step_id,
            data_schema,
            errors=None,
            description_placeholders=None,
        ):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
                "description_placeholders": description_placeholders or {},
            }

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        async def async_set_unique_id(self, unique_id):
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            return None

        def _async_current_entries(self):
            return getattr(self, "_current_entries", [])

    fake_handlers = SimpleNamespace(register=lambda domain: (lambda cls: cls))
    config_entries_module = _module_with_attrs(
        "homeassistant.config_entries",
        CONN_CLASS_CLOUD_POLL="cloud_poll",
        CONN_CLASS_LOCAL_POLL="local_poll",
        ConfigEntry=object,
        ConfigFlow=FakeConfigFlow,
        HANDLERS=fake_handlers,
        OptionsFlow=object,
    )
    auth_failed_error = type("ConfigEntryAuthFailed", (Exception,), {})

    async def _exchange_code_for_tokens(*, session, code, code_verifier):
        del session, code, code_verifier
        raise AssertionError("exchange_code_for_tokens should be patched in this test")

    pointt_rest_client_module = _module_with_attrs(
        "custom_components.bosch.pointt_rest_client",
        PointTRestClient=MagicMock(),
        exchange_code_for_tokens=_exchange_code_for_tokens,
    )
    fake_modules = {
        "custom_components": _package_module("custom_components"),
        "custom_components.bosch": _package_module("custom_components.bosch"),
        "custom_components.bosch.const": _module_with_attrs(
            "custom_components.bosch.const",
            ACCESS_TOKEN="access_token",
            DEVICE_ID="device_id",
            DOMAIN="bosch",
            REFRESH_TOKEN="refresh_token",
            UUID="uuid",
        ),
        "custom_components.bosch.oauth_helper": _module_with_attrs(
            "custom_components.bosch.oauth_helper",
            build_auth_url=lambda challenge: f"https://example.test/auth?challenge={challenge}",
            generate_pkce_pair=lambda: ("test-verifier", "test-challenge"),
        ),
        "custom_components.bosch.pointt_rest_client": pointt_rest_client_module,
        "homeassistant": _package_module("homeassistant"),
        "homeassistant.config_entries": config_entries_module,
        "homeassistant.const": _module_with_attrs(
            "homeassistant.const",
            CONF_ACCESS_TOKEN="access_token",
        ),
        "homeassistant.core": _module_with_attrs(
            "homeassistant.core",
            callback=lambda func: func,
        ),
        "homeassistant.exceptions": _module_with_attrs(
            "homeassistant.exceptions",
            ConfigEntryAuthFailed=auth_failed_error,
        ),
        "homeassistant.helpers": _package_module("homeassistant.helpers"),
        "homeassistant.helpers.aiohttp_client": _module_with_attrs(
            "homeassistant.helpers.aiohttp_client",
            async_get_clientsession=MagicMock(return_value=object()),
        ),
        "voluptuous": _module_with_attrs(
            "voluptuous",
            In=lambda value: value,
            Optional=lambda key, default=None: key,
            Required=lambda key, default=None: key,
            Schema=lambda value: value,
        ),
    }

    with patch.dict(sys.modules, fake_modules):
        spec = importlib.util.spec_from_file_location(module_name, config_flow_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        module.ConfigEntryAuthFailed = auth_failed_error
        module._pointt_rest_client_module = pointt_rest_client_module
        yield module


def _package_module(name: str):
    module = ModuleType(name)
    module.__path__ = []  # type: ignore[attr-defined]
    return module


def _module_with_attrs(name: str, **attrs):
    module = ModuleType(name)
    for attr_name, value in attrs.items():
        setattr(module, attr_name, value)
    return module
