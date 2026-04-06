"""REST Gateway Wrapper for OAuth2 API client."""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from .const import DEVICE_ID, UUID
from .rest_dhw_circuit import RestDhwCircuit
from .rest_heating_circuit import RestHeatingCircuit
from .rest_zone import RestZone

if TYPE_CHECKING:
    from .pointt_rest_client import PointTRestClient

_LOGGER = logging.getLogger(__name__)


class RestGatewayWrapper:
    """Gateway wrapper for modeled CT200 PointT resources."""

    SYSTEM_CONTROL_ENDPOINTS = [
        "/devices/device1/thermostat/childLock/enabled",
        "/system/awayMode/enabled",
        "/system/autoAway/enabled",
        "/system/openWindowDetection/enabled",
        "/gateway/notificationLight/enabled",
        "/system/sensors/temperatures/offset",
        "/system/awayMode/temperature",
        "/system/openWindowDetection/duration",
        "/system/openWindowDetection/temperature",
        "/gateway/pirSensitivity",
        "/gateway/ui/splashScreen",
    ]
    SYSTEM_SENSOR_ENDPOINTS = [
        "/system/sensors/humidity/indoor_h1",
        "/system/sensors/temperatures/outdoor_t1",
        "/system/sensors/temperatures/indoorAirDigital",
        "/system/sensors/temperatures/indoorChip",
        "/system/sensors/temperatures/indoorPCB",
    ]
    SYSTEM_ENDPOINTS = [*SYSTEM_CONTROL_ENDPOINTS, *SYSTEM_SENSOR_ENDPOINTS]
    ZONE_CORE_ENDPOINTS = [
        "/zones/zn1/temperatureActual",
        "/zones/zn1/temperatureHeatingSetpoint",
        "/zones/zn1/userMode",
        "/zones/zn1/status",
        "/zones/zn1/name",
        "/zones/zn1/actualValvePosition",
        "/zones/zn1/timeToNextSetpoint",
        "/zones/zn1/optimumStartState",
        "/zones/zn1/optimumStartHeatupRate",
        "/zones/zn1/openWindowDetection/enabled",
        "/zones/zn1/openWindowDetection/status",
    ]
    ZONE_SUPPLEMENTAL_ENDPOINTS = [
        "/zones/zn1/nextSetpoint",
        "/zones/zn1/manualTemperatureHeating",
        "/zones/zn1/clockProgram",
        "/zones/zn1/clockOverride/temperatureHeating",
        "/zones/zn1/icon",
        "/zones/zn1/heatingType",
    ]
    ZONE_ENDPOINTS = [*ZONE_CORE_ENDPOINTS, *ZONE_SUPPLEMENTAL_ENDPOINTS]
    HEATING_CIRCUIT_CORE_ENDPOINTS = [
        "/heatingCircuits/hc1/supplyTemperatureSetpoint",
        "/heatingCircuits/hc1/minOutdoorTemp",
        "/heatingCircuits/hc1/nightThreshold",
        "/heatingCircuits/hc1/suWiThreshold",
        "/heatingCircuits/hc1/boostMode",
        "/heatingCircuits/hc1/operatingSeason",
        "/heatingCircuits/hc1/boostRemainingTime",
    ]
    HEATING_CIRCUIT_SUPPLEMENTAL_ENDPOINTS = [
        "/heatingCircuits/hc1/heatCurveMax",
        "/heatingCircuits/hc1/heatCurveMin",
        "/heatingCircuits/hc1/maxSupply",
        "/heatingCircuits/hc1/minSupply",
        "/heatingCircuits/hc1/roomInfluence",
        "/heatingCircuits/hc1/nightSwitchMode",
        "/heatingCircuits/hc1/suWiSwitchMode",
        "/heatingCircuits/hc1/type",
        "/heatingCircuits/hc1/control",
        "/heatingCircuits/hc1/buildingHeatup",
        "/heatingCircuits/hc1/setpointOptimization",
        "/heatingCircuits/hc1/boostDuration",
        "/heatingCircuits/hc1/boostTemperature",
    ]
    HEATING_CIRCUIT_ENDPOINTS = [
        *HEATING_CIRCUIT_CORE_ENDPOINTS,
        *HEATING_CIRCUIT_SUPPLEMENTAL_ENDPOINTS,
    ]
    DHW_CORE_ENDPOINTS = [
        "/dhwCircuits/dhw1/actualTemp",
        "/dhwCircuits/dhw1/hotWaterSystem",
        "/dhwCircuits/dhw1/state",
        "/dhwCircuits/dhw1/thermalDisinfect/lastResult",
        "/dhwCircuits/dhw1/thermalDisinfect/state",
        "/dhwCircuits/dhw1/thermalDisinfect/time",
        "/dhwCircuits/dhw1/thermalDisinfect/weekDay",
    ]
    DHW_SUPPLEMENTAL_ENDPOINTS = [
        "/dhwCircuits/dhw1/operationMode",
        "/dhwCircuits/dhw1/extraDhw",
        "/dhwCircuits/dhw1/extraDhwDuration",
        "/dhwCircuits/dhw1/temperatureLevels/high",
    ]
    DHW_ENDPOINTS = [*DHW_CORE_ENDPOINTS, *DHW_SUPPLEMENTAL_ENDPOINTS]
    MODELLED_ENDPOINTS = [
        *ZONE_ENDPOINTS,
        *SYSTEM_ENDPOINTS,
        *HEATING_CIRCUIT_ENDPOINTS,
        *DHW_ENDPOINTS,
    ]
    BULK_REQUEST_GROUPS = {
        "zone_core": ZONE_CORE_ENDPOINTS,
        "system_sensors": SYSTEM_SENSOR_ENDPOINTS,
        "heating_circuit_core": HEATING_CIRCUIT_CORE_ENDPOINTS,
        "dhw_core": DHW_CORE_ENDPOINTS,
        "system_controls": SYSTEM_CONTROL_ENDPOINTS,
        "zone_supplemental": ZONE_SUPPLEMENTAL_ENDPOINTS,
        "heating_circuit_supplemental": HEATING_CIRCUIT_SUPPLEMENTAL_ENDPOINTS,
        "dhw_supplemental": DHW_SUPPLEMENTAL_ENDPOINTS,
    }
    BULK_PRIMARY_ENDPOINTS = [
        path
        for paths in BULK_REQUEST_GROUPS.values()
        for path in paths
    ]
    BULK_BLACKLIST = {"/zones/zn1/humidity"}

    def __init__(self, client: PointTRestClient, entry: ConfigEntry):  # type: ignore[name-defined]
        """Initialize the gateway wrapper.

        Args:
            client: PointTRestClient instance
            entry: Config entry for this integration

        Raises:
            ValueError: If config entry is missing required keys
        """
        self.client = client
        self.entry = entry
        self.uuid = entry.data.get(UUID)
        self.device_id = entry.data.get(DEVICE_ID)
        if not self.uuid or not self.device_id:
            _LOGGER.error("Config entry missing required keys: uuid=%s, device_id=%s", self.uuid, self.device_id)
            raise ValueError("Invalid config entry: missing uuid or device_id")
        self._zones = {}
        self._resource_cache: dict[str, Any] = {}
        self._bulk_blacklist: set[str] = set(self.BULK_BLACKLIST)
        self._heating_circuits = []
        self._rest_heating_circuits = []
        self._dhw_circuits = []
        self.device_name = None
        self.firmware = None
        self.product_id = None
        self.device_model = "Bosch"  # Manufacturer name
        self.device_type = "CT200 (EasyControl)"  # Model name

        _LOGGER.debug("Initialized RestGatewayWrapper for device %s", self.device_id)

    @property
    def heating_circuits(self):
        """Return the climate-facing circuit list."""
        return self._heating_circuits

    @property
    def zones(self):
        """Return zones list."""
        return list(self._zones.values())

    @property
    def dhw_circuits(self):
        """Return DHW circuits."""
        return self._dhw_circuits

    @property
    def rest_heating_circuits(self):
        """Return REST heating circuits list."""
        return self._rest_heating_circuits

    @property
    def system_cache(self) -> dict[str, Any]:
        """Return the system endpoint cache (read-only view)."""
        return {
            path: payload
            for path, payload in self._resource_cache.items()
            if path in self.SYSTEM_ENDPOINTS
        }

    @property
    def bulk_cache(self) -> dict[str, Any]:
        """Return the bulk cache (read-only view)."""
        return self._resource_cache

    @property
    def bulk_blacklist(self) -> set[str]:
        """Return blacklisted bulk endpoints."""
        return self._bulk_blacklist

    async def initialize(self) -> bool:
        """Initialize the gateway - fetch device info and create zone objects.

        Returns:
            True if successful
        """
        try:
            device_info = await self.client.get_device_info()
            self.device_name = f"Bosch CT200 ({self.device_id})"
            self.firmware = device_info.get("firmware")
            self.product_id = device_info.get("product_id")

            # Create the modeled zone.
            zone = RestZone(
                client=self.client,
                zone_id="zn1",
                device_id=self.device_id,
                gateway_wrapper=self,
            )

            # Initialize zone
            if await zone.initialize():
                self._zones["zn1"] = zone
                self._heating_circuits.append(zone)
                _LOGGER.debug("Created and initialized zone zn1")
            else:
                _LOGGER.warning("Failed to initialize zone zn1")

            # Create the modeled heating circuit.
            hc = RestHeatingCircuit(
                client=self.client,
                hc_id="hc1",
                device_id=self.device_id,
                gateway_wrapper=self,
            )

            # Initialize heating circuit
            if await hc.initialize():
                self._rest_heating_circuits.append(hc)
                _LOGGER.debug("Created and initialized heating circuit hc1")
            else:
                _LOGGER.warning("Failed to initialize heating circuit hc1")

            # Create the modeled DHW circuit.
            dhw = RestDhwCircuit(
                client=self.client,
                dhw_id="dhw1",
                device_id=self.device_id,
                gateway_wrapper=self,
            )

            # Initialize DHW circuit
            if await dhw.initialize():
                self._dhw_circuits.append(dhw)
                _LOGGER.debug("Created and initialized DHW circuit dhw1")
            else:
                _LOGGER.warning("Failed to initialize DHW circuit dhw1")

            _LOGGER.info(
                "Initialized gateway %s (firmware: %s, zones: %d, REST heating circuits: %d, DHW circuits: %d)",
                self.device_id,
                self.firmware,
                len(self._zones),
                len(self._rest_heating_circuits),
                len(self._dhw_circuits),
            )
            return True

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to initialize gateway: %s", err)
            return False

    def get_cached_resource(self, path: str) -> dict[str, Any] | None:
        """Return a cached resource payload if available."""
        return self._resource_cache.get(path)

    @staticmethod
    def _extract_bulk_payloads(response_data: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Normalize bulk response into successful payloads and failures."""
        payloads: dict[str, Any] = {}
        failures: dict[str, Any] = {}

        if not isinstance(response_data, list):
            return payloads, {"__root__": response_data}

        for gateway_entry in response_data:
            if not isinstance(gateway_entry, dict):
                continue
            for resource_entry in gateway_entry.get("resourcePaths", []):
                if not isinstance(resource_entry, dict):
                    continue
                path = resource_entry.get("resourcePath")
                if not isinstance(path, str):
                    continue
                server_status = resource_entry.get("serverStatus")
                gateway_response = resource_entry.get("gatewayResponse")
                if (
                    server_status == 200
                    and isinstance(gateway_response, dict)
                    and gateway_response.get("status") == 200
                    and isinstance(gateway_response.get("payload"), dict)
                ):
                    payloads[path] = gateway_response["payload"]
                else:
                    failures[path] = resource_entry

        return payloads, failures

    async def _update_bulk_cache(self) -> set[str]:
        """Fetch the CT200 payload set via PointT bulk requests."""
        failed_paths: set[str] = set()
        if not hasattr(self.client, "post_bulk_resources"):
            return failed_paths

        seen_paths: set[str] = set()
        for group_name, group_paths in self.BULK_REQUEST_GROUPS.items():
            bulk_paths = [
                path
                for path in group_paths
                if path not in self._bulk_blacklist and path not in seen_paths
            ]
            if not bulk_paths:
                continue

            response_data = None
            for attempt in range(2):
                try:
                    response_data = await self.client.post_bulk_resources(bulk_paths)
                    break
                except Exception as err:  # pylint: disable=broad-except
                    if attempt == 1:
                        failed_paths.update(bulk_paths)
                        _LOGGER.warning(
                            "Bulk fetch failed for %s group %s (%d endpoints): %s",
                            self.device_id,
                            group_name,
                            len(bulk_paths),
                            err,
                        )
                        _LOGGER.debug(
                            "Rejected bulk group %s endpoints: %s",
                            group_name,
                            bulk_paths,
                        )
                        response_data = None

            if response_data is None:
                continue

            payloads, failures = self._extract_bulk_payloads(response_data)
            self._resource_cache.update(payloads)
            seen_paths.update(payloads)

            for path, failure in failures.items():
                failed_paths.add(path)
                if isinstance(failure, dict) and failure.get("serverStatus") == 403:
                    self._bulk_blacklist.add(path)

        return failed_paths

    async def set_resource_value(self, path: str, value: Any) -> bool:
        """Write a value and optimistically update the local cache."""
        result = await self.client.set_resource(path, value)
        if result:
            cached = dict(self._resource_cache.get(path, {}))
            cached["id"] = path
            cached["value"] = value
            self._resource_cache[path] = cached
        return result

    async def update(self) -> None:
        """Update all gateway data.

        Fetches latest zone, circuit, and system endpoint data from the API.
        """
        try:
            await self._update_bulk_cache()

            # Update all zone objects
            for zone in self._zones.values():
                await zone.update()

            # Update all REST heating circuit objects
            for hc in self._rest_heating_circuits:
                await hc.update()

            # Update all DHW circuit objects
            for dhw in self._dhw_circuits:
                await dhw.update()

            _LOGGER.debug("Updated gateway data for %s", self.device_id)

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error updating gateway data: %s", err)
            raise

    async def close(self) -> None:
        """Close the gateway and cleanup resources."""
        try:
            # PointTRestClient uses hass session, no need to close
            _LOGGER.debug("Closed RestGatewayWrapper for device %s", self.device_id)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error closing gateway: %s", err)
