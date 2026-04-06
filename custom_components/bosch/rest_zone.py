"""REST API Zone wrapper for OAuth2 authentication."""
from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pointt_rest_client import PointTRestClient

_LOGGER = logging.getLogger(__name__)


class RestZone:
    """Zone wrapper for modeled CT200 resources."""

    def __init__(
        self,
        client: PointTRestClient,
        zone_id: str,
        device_id: str,
        gateway_wrapper=None,
    ):
        """Initialize REST zone.

        Args:
            client: PointTRestClient instance
            zone_id: Zone identifier (e.g., "zn1")
            device_id: Device ID for logging
        """
        self.client = client
        self._gateway_wrapper = gateway_wrapper
        self.zone_id = zone_id
        self.device_id = device_id
        self.attr_id = f"/zones/{zone_id}"  # Used by climate platform for naming

        # Zone data cache
        self._data: dict[str, Any] = {}
        self._name: str | None = None
        self._current_temp: float | None = None
        self._target_temp: float | None = None
        self._hvac_action: str | None = None
        self._hvac_mode: str | None = None
        self._min_temp: float = 5.0
        self._max_temp: float = 30.0
        self._update_initialized: bool = False

        # Additional sensor data
        self._valve_position: float | None = None
        self._next_setpoint: float | None = None
        self._time_to_next_setpoint: float | None = None
        self._optimum_start_state: str | None = None
        self._optimum_start_heatup_rate: float | None = None
        self._window_detection_enabled: bool | None = None
        self._window_detection_status: bool | None = None

        # Control/number entity data
        self._manual_temp_heating: float | None = None
        self._clock_program: float | None = None
        self._clock_override_temp: float | None = None

        _LOGGER.debug("Created RestZone for %s on device %s", zone_id, device_id)

    async def _get_resource(self, path: str) -> dict[str, Any] | None:
        """Read a resource from the gateway cache."""
        if self._gateway_wrapper is not None:
            return self._gateway_wrapper.get_cached_resource(path)
        return await self.client.get_resource(path)

    @property
    def id(self) -> str:
        """Return zone ID for unique entity ID."""
        return self.zone_id

    @property
    def parent_id(self) -> str | None:
        """Return parent ID (zones don't have parents)."""
        return None

    @property
    def name(self) -> str:
        """Return zone name."""
        return self._name or f"Zone {self.zone_id}"

    @property
    def state(self) -> bool:
        """Return zone state (on/off)."""
        # Zone is "on" if it has valid data
        return bool(self._data)

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        return self._current_temp

    @property
    def current_temp(self) -> float | None:
        """Return current temperature (alias for current_temperature)."""
        return self._current_temp

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return self._target_temp

    @property
    def min_temp(self) -> float:
        """Return minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self) -> float:
        """Return maximum temperature."""
        return self._max_temp

    @property
    def hvac_action(self) -> str | None:
        """Return current HVAC action (heating/idle/off)."""
        return self._hvac_action

    @property
    def hvac_mode(self) -> str | None:
        """Return current HVAC mode (heat/auto/off)."""
        return self._hvac_mode

    @property
    def ha_mode(self) -> str | None:
        """Return current HA mode (alias for hvac_mode)."""
        return self._hvac_mode

    @property
    def ha_modes(self) -> list[str]:
        """Return supported HA HVAC modes."""
        # CT200 supports: off, heat, auto
        return ["off", "heat", "auto"]

    @property
    def support_target_temp(self) -> bool:
        """Return if target temperature can be set."""
        return True

    @property
    def setpoint(self) -> str:
        """Return current setpoint/mode name.

        This is displayed in the climate entity's state attributes.
        """
        # Return the current operation mode or preset as the setpoint
        if self._hvac_mode:
            return self._hvac_mode
        return "unknown"

    @property
    def support_presets(self) -> bool:
        """Return if presets are supported."""
        return False

    @property
    def preset_modes(self) -> list[str]:
        """Return available preset modes."""
        return []

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        return None

    @property
    def update_initialized(self) -> bool:
        """Return whether zone has been successfully updated at least once."""
        return self._update_initialized

    @property
    def temp_units(self) -> str:
        """Return temperature units."""
        return "C"

    @property
    def valve_position(self) -> float | None:
        """Return valve position percentage (0-100)."""
        return self._valve_position

    @property
    def next_setpoint_temp(self) -> float | None:
        """Return next scheduled setpoint temperature."""
        return self._next_setpoint

    @property
    def time_to_next_setpoint(self) -> float | None:
        """Return minutes until next setpoint change."""
        return self._time_to_next_setpoint

    @property
    def optimum_start_active(self) -> bool:
        """Return whether optimum start is active."""
        return self._optimum_start_state == "on" if self._optimum_start_state else False

    @property
    def window_detection_enabled(self) -> bool | None:
        """Return whether window detection is enabled."""
        return self._window_detection_enabled

    @property
    def window_open(self) -> bool | None:
        """Return whether window is detected as open."""
        return self._window_detection_status

    @property
    def optimum_start_heatup_rate(self) -> float | None:
        """Return optimum start heatup rate in s/K."""
        return self._optimum_start_heatup_rate

    @property
    def manual_temp_heating(self) -> float | None:
        """Return manual heating temperature setpoint."""
        return self._manual_temp_heating

    @property
    def clock_program(self) -> float | None:
        """Return current clock program number."""
        return self._clock_program

    @property
    def clock_override_temp(self) -> float | None:
        """Return clock override temperature."""
        return self._clock_override_temp

    async def initialize(self) -> bool:
        """Initialize zone - fetch initial data.

        Returns:
            True if successful
        """
        try:
            await self.update()
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to initialize zone %s: %s", self.zone_id, err)
            return False

    async def update(self) -> None:
        """Update zone data from API.

        The modeled resources are refreshed by exact endpoint path.
        """
        try:
            # Fetch individual zone resources
            # The zone root returns a refEnum with references, not actual data
            current_temp_data = await self._get_resource(f"/zones/{self.zone_id}/temperatureActual")
            target_temp_data = await self._get_resource(f"/zones/{self.zone_id}/temperatureHeatingSetpoint")
            user_mode_data = await self._get_resource(f"/zones/{self.zone_id}/userMode")
            status_data = await self._get_resource(f"/zones/{self.zone_id}/status")
            name_data = await self._get_resource(f"/zones/{self.zone_id}/name")

            # Parse temperature values
            if current_temp_data and "value" in current_temp_data:
                self._current_temp = float(current_temp_data["value"])
            else:
                _LOGGER.debug("No current temperature data for %s", self.zone_id)

            if target_temp_data and "value" in target_temp_data:
                self._target_temp = float(target_temp_data["value"])
            else:
                _LOGGER.debug("No target temperature data for %s", self.zone_id)

            # Parse zone name (API returns base64 encoded names)
            if name_data and "value" in name_data:
                try:
                    name_encoded = name_data["value"]
                    name_decoded = base64.b64decode(name_encoded).decode("utf-8")
                    self._name = name_decoded
                    _LOGGER.debug("Decoded zone name: %s -> %s", name_encoded, name_decoded)
                except Exception:
                    self._name = name_data["value"]

            # Parse user mode and map to HA HVAC mode
            if user_mode_data and "value" in user_mode_data:
                mode_value = user_mode_data["value"]
                self._hvac_mode = self._map_mode_to_ha(mode_value)
                _LOGGER.debug("Zone %s mode: %s -> %s", self.zone_id, mode_value, self._hvac_mode)

            # Parse status for HVAC action
            if status_data and "value" in status_data:
                status_value = status_data["value"]
                self._hvac_action = self._map_status_to_action(status_value)

            # Fetch additional sensor data
            valve_data = await self._get_resource(f"/zones/{self.zone_id}/actualValvePosition")
            if valve_data and "value" in valve_data:
                self._valve_position = float(valve_data["value"])

            next_setpoint_data = await self._get_resource(f"/zones/{self.zone_id}/nextSetpoint")
            if next_setpoint_data and "value" in next_setpoint_data:
                self._next_setpoint = float(next_setpoint_data["value"])

            time_to_next_data = await self._get_resource(f"/zones/{self.zone_id}/timeToNextSetpoint")
            if time_to_next_data and "value" in time_to_next_data:
                self._time_to_next_setpoint = float(time_to_next_data["value"])

            optimum_start_data = await self._get_resource(f"/zones/{self.zone_id}/optimumStartState")
            if optimum_start_data and "value" in optimum_start_data:
                self._optimum_start_state = optimum_start_data["value"]

            heatup_rate_data = await self._get_resource(f"/zones/{self.zone_id}/optimumStartHeatupRate")
            if heatup_rate_data and "value" in heatup_rate_data:
                self._optimum_start_heatup_rate = float(heatup_rate_data["value"])

            # Window detection has sub-resources
            try:
                window_enabled_data = await self._get_resource(
                    f"/zones/{self.zone_id}/openWindowDetection/enabled"
                )
                if window_enabled_data and "value" in window_enabled_data:
                    self._window_detection_enabled = window_enabled_data["value"] == "on"

                window_status_data = await self._get_resource(
                    f"/zones/{self.zone_id}/openWindowDetection/status"
                )
                if window_status_data and "value" in window_status_data:
                    self._window_detection_status = window_status_data["value"] == "open"
            except Exception as err:
                _LOGGER.debug("Could not fetch window detection data: %s", err)

            # Fetch control/number entity values
            manual_temp_data = await self._get_resource(f"/zones/{self.zone_id}/manualTemperatureHeating")
            if manual_temp_data and "value" in manual_temp_data:
                self._manual_temp_heating = float(manual_temp_data["value"])

            clock_program_data = await self._get_resource(f"/zones/{self.zone_id}/clockProgram")
            if clock_program_data and "value" in clock_program_data:
                self._clock_program = float(clock_program_data["value"])

            clock_override_data = await self._get_resource(
                f"/zones/{self.zone_id}/clockOverride/temperatureHeating"
            )
            if clock_override_data and "value" in clock_override_data:
                self._clock_override_temp = float(clock_override_data["value"])

            # Mark as initialized after successful update
            self._update_initialized = True

            _LOGGER.debug(
                "Updated zone %s: current=%s, target=%s, mode=%s, action=%s",
                self.zone_id,
                self._current_temp,
                self._target_temp,
                self._hvac_mode,
                self._hvac_action,
            )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error updating zone %s: %s", self.zone_id, err)
            raise

    def _map_mode_to_ha(self, mode_value: str) -> str:
        """Map PointT API mode to Home Assistant HVAC mode.

        Args:
            mode_value: Mode value from API (e.g., "manual", "automatic", "off")

        Returns:
            HA HVAC mode: "heat", "auto", or "off"
        """
        mode_map = {
            "manual": "heat",
            "automatic": "auto",
            "off": "off",
        }
        return mode_map.get(mode_value.lower(), "heat")

    def _map_status_to_action(self, status_value: str) -> str:
        """Map PointT API status to HA HVAC action.

        Args:
            status_value: Status from API

        Returns:
            HA HVAC action: "heating", "idle", or "off"
        """
        if status_value and "heat" in status_value.lower():
            return "heating"
        elif status_value and "idle" in status_value.lower():
            return "idle"
        return "idle"

    async def set_temperature(self, temperature: float) -> bool:
        """Set target temperature."""
        try:
            if not (self.min_temp <= temperature <= self.max_temp):
                _LOGGER.error(
                    "Temperature %s out of range [%s, %s]",
                    temperature,
                    self.min_temp,
                    self.max_temp,
                )
                return False

            path = f"/zones/{self.zone_id}/temperatureHeatingSetpoint"
            if self._gateway_wrapper is not None:
                result = await self._gateway_wrapper.set_resource_value(path, temperature)
            else:
                result = await self.client.set_resource(path, temperature)

            if result:
                # Update cached value
                self._target_temp = temperature
                _LOGGER.info("Set temperature for %s to %s", self.zone_id, temperature)
                return True

            return False

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error setting temperature for %s: %s", self.zone_id, err)
            return False

    async def set_ha_mode(self, mode: str) -> bool:
        """Set HVAC mode."""
        try:
            mode_map = {
                "heat": "manual",
                "auto": "automatic",
                "off": "off",
            }
            api_mode = mode_map.get(mode)
            if api_mode is None:
                _LOGGER.error("Unsupported HVAC mode for %s: %s", self.zone_id, mode)
                return False

            path = f"/zones/{self.zone_id}/userMode"
            if self._gateway_wrapper is not None:
                result = await self._gateway_wrapper.set_resource_value(path, api_mode)
            else:
                result = await self.client.set_resource(path, api_mode)

            if result:
                self._hvac_mode = mode
                _LOGGER.info("Set HVAC mode for %s to %s", self.zone_id, mode)
                return True

            return False

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error setting mode for %s: %s", self.zone_id, err)
            return False
