"""REST API DHW Circuit wrapper for OAuth2 authentication."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pointt_rest_client import PointTRestClient

_LOGGER = logging.getLogger(__name__)


class RestDhwCircuit:
    """DHW wrapper for modeled CT200 resources."""

    def __init__(
        self,
        client: PointTRestClient,
        dhw_id: str,
        device_id: str,
        gateway_wrapper=None,
    ):
        """Initialize REST DHW circuit.

        Args:
            client: PointTRestClient instance
            dhw_id: DHW circuit identifier (e.g., "dhw1")
            device_id: Device ID for logging
        """
        self.client = client
        self._gateway_wrapper = gateway_wrapper
        self.dhw_id = dhw_id
        self.device_id = device_id
        self.attr_id = f"/dhwCircuits/{dhw_id}"

        # DHW circuit data cache
        self._actual_temp: float | None = None
        self._hot_water_system: str | None = None
        self._state: str | None = None
        self._operation_mode: str | None = None

        # Extra DHW (boost)
        self._extra_dhw: str | None = None
        self._extra_dhw_duration: float | None = None

        # Temperature levels
        self._temp_high: float | None = None

        # Thermal disinfect
        self._thermal_disinfect_state: str | None = None
        self._thermal_disinfect_weekday: str | None = None
        self._thermal_disinfect_time: float | None = None
        self._thermal_disinfect_last_result: str | None = None

        self._update_initialized: bool = False
        self._name = f"Domestic Hot Water ({dhw_id})"

        _LOGGER.debug("Created RestDhwCircuit for %s on device %s", dhw_id, device_id)

    async def _get_resource(self, path: str) -> dict[str, Any] | None:
        """Read a resource from the gateway cache."""
        if self._gateway_wrapper is not None:
            return self._gateway_wrapper.get_cached_resource(path)
        return await self.client.get_resource(path)

    @property
    def id(self) -> str:
        """Return DHW circuit ID."""
        return self.dhw_id

    @property
    def name(self) -> str:
        """Return DHW circuit name."""
        return self._name

    @property
    def parent_id(self) -> str | None:
        """Return parent ID (DHW circuits don't have parents)."""
        return None

    @property
    def update_initialized(self) -> bool:
        """Return whether DHW has been successfully updated at least once."""
        return self._update_initialized

    # Sensor properties
    @property
    def actual_temp(self) -> float | None:
        """Return actual water temperature."""
        return self._actual_temp

    @property
    def hot_water_system(self) -> str | None:
        """Return hot water system type."""
        return self._hot_water_system

    @property
    def state(self) -> str | None:
        """Return DHW state."""
        return self._state

    @property
    def operation_mode(self) -> str | None:
        """Return operation mode."""
        return self._operation_mode

    @property
    def extra_dhw(self) -> str | None:
        """Return extra DHW boost state."""
        return self._extra_dhw

    @property
    def extra_dhw_duration(self) -> float | None:
        """Return extra DHW duration in minutes."""
        return self._extra_dhw_duration

    @property
    def temp_high(self) -> float | None:
        """Return high temperature level."""
        return self._temp_high

    @property
    def thermal_disinfect_state(self) -> str | None:
        """Return thermal disinfect state."""
        return self._thermal_disinfect_state

    @property
    def thermal_disinfect_weekday(self) -> str | None:
        """Return thermal disinfect weekday."""
        return self._thermal_disinfect_weekday

    @property
    def thermal_disinfect_time(self) -> float | None:
        """Return thermal disinfect time in minutes."""
        return self._thermal_disinfect_time

    @property
    def thermal_disinfect_last_result(self) -> str | None:
        """Return last thermal disinfect result."""
        return self._thermal_disinfect_last_result

    async def initialize(self) -> bool:
        """Initialize DHW circuit - fetch initial data.

        Returns:
            True if successful
        """
        try:
            await self.update()
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to initialize DHW circuit %s: %s", self.dhw_id, err)
            return False

    async def update(self) -> None:
        """Update DHW circuit data from API."""
        try:
            # Fetch sensor values
            actual_temp_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/actualTemp")
            if actual_temp_data and "value" in actual_temp_data:
                self._actual_temp = float(actual_temp_data["value"])

            hot_water_system_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/hotWaterSystem")
            if hot_water_system_data and "value" in hot_water_system_data:
                self._hot_water_system = hot_water_system_data["value"]

            state_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/state")
            if state_data and "value" in state_data:
                self._state = state_data["value"]

            # Fetch operation mode
            operation_mode_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/operationMode")
            if operation_mode_data and "value" in operation_mode_data:
                self._operation_mode = operation_mode_data["value"]

            # Fetch extra DHW settings
            extra_dhw_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/extraDhw")
            if extra_dhw_data and "value" in extra_dhw_data:
                self._extra_dhw = extra_dhw_data["value"]

            extra_dhw_duration_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/extraDhwDuration")
            if extra_dhw_duration_data and "value" in extra_dhw_duration_data:
                self._extra_dhw_duration = float(extra_dhw_duration_data["value"])

            # Fetch temperature levels
            temp_high_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/temperatureLevels/high")
            if temp_high_data and "value" in temp_high_data:
                self._temp_high = float(temp_high_data["value"])

            # Fetch thermal disinfect settings
            thermal_state_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/thermalDisinfect/state")
            if thermal_state_data and "value" in thermal_state_data:
                self._thermal_disinfect_state = thermal_state_data["value"]

            thermal_weekday_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/thermalDisinfect/weekDay")
            if thermal_weekday_data and "value" in thermal_weekday_data:
                self._thermal_disinfect_weekday = thermal_weekday_data["value"]

            thermal_time_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/thermalDisinfect/time")
            if thermal_time_data and "value" in thermal_time_data:
                self._thermal_disinfect_time = float(thermal_time_data["value"])

            thermal_result_data = await self._get_resource(f"/dhwCircuits/{self.dhw_id}/thermalDisinfect/lastResult")
            if thermal_result_data and "value" in thermal_result_data:
                self._thermal_disinfect_last_result = thermal_result_data["value"]

            self._update_initialized = True

            _LOGGER.debug(
                "Updated DHW circuit %s: actual_temp=%s, state=%s, mode=%s",
                self.dhw_id,
                self._actual_temp,
                self._state,
                self._operation_mode,
            )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error updating DHW circuit %s: %s", self.dhw_id, err)
            # Don't raise - allow partial updates
