"""REST API Heating Circuit wrapper for OAuth2 authentication."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pointt_rest_client import PointTRestClient

_LOGGER = logging.getLogger(__name__)


class RestHeatingCircuit:
    """Heating circuit wrapper for modeled CT200 resources."""

    def __init__(
        self,
        client: PointTRestClient,
        hc_id: str,
        device_id: str,
        gateway_wrapper=None,
    ):
        """Initialize REST heating circuit.

        Args:
            client: PointTRestClient instance
            hc_id: Heating circuit identifier (e.g., "hc1")
            device_id: Device ID for logging
        """
        self.client = client
        self._gateway_wrapper = gateway_wrapper
        self.hc_id = hc_id
        self.device_id = device_id
        self.attr_id = f"/heatingCircuits/{hc_id}"

        # Heating circuit data cache
        self._heat_curve_max: float | None = None
        self._heat_curve_min: float | None = None
        self._max_supply: float | None = None
        self._min_supply: float | None = None
        self._supply_temp_setpoint: float | None = None
        self._room_influence: float | None = None
        self._min_outdoor_temp: float | None = None
        self._night_threshold: float | None = None
        self._suwi_threshold: float | None = None

        # Mode/select values
        self._boost_mode: str | None = None
        self._operating_season: str | None = None
        self._night_switch_mode: str | None = None
        self._suwi_switch_mode: str | None = None
        self._circuit_type: str | None = None
        self._control: str | None = None
        self._building_heatup: str | None = None
        self._setpoint_optimization: str | None = None

        # Boost settings
        self._boost_duration: float | None = None
        self._boost_temperature: float | None = None
        self._boost_remaining_time: float | None = None

        self._update_initialized: bool = False
        self._name = f"Heating Circuit {hc_id}"

        _LOGGER.debug("Created RestHeatingCircuit for %s on device %s", hc_id, device_id)

    async def _get_resource(self, path: str) -> dict[str, Any] | None:
        """Read a resource from the gateway cache."""
        if self._gateway_wrapper is not None:
            return self._gateway_wrapper.get_cached_resource(path)
        return await self.client.get_resource(path)

    @property
    def id(self) -> str:
        """Return heating circuit ID."""
        return self.hc_id

    @property
    def name(self) -> str:
        """Return heating circuit name."""
        return self._name

    @property
    def parent_id(self) -> str | None:
        """Return parent ID (heating circuits don't have parents)."""
        return None

    @property
    def update_initialized(self) -> bool:
        """Return whether HC has been successfully updated at least once."""
        return self._update_initialized

    # Heating curve properties
    @property
    def heat_curve_max(self) -> float | None:
        """Return maximum heating curve value."""
        return self._heat_curve_max

    @property
    def heat_curve_min(self) -> float | None:
        """Return minimum heating curve value."""
        return self._heat_curve_min

    # Temperature properties
    @property
    def max_supply(self) -> float | None:
        """Return maximum supply temperature."""
        return self._max_supply

    @property
    def min_supply(self) -> float | None:
        """Return minimum supply temperature."""
        return self._min_supply

    @property
    def supply_temp_setpoint(self) -> float | None:
        """Return supply temperature setpoint."""
        return self._supply_temp_setpoint

    @property
    def min_outdoor_temp(self) -> float | None:
        """Return minimum outdoor temperature."""
        return self._min_outdoor_temp

    @property
    def night_threshold(self) -> float | None:
        """Return night threshold temperature."""
        return self._night_threshold

    @property
    def suwi_threshold(self) -> float | None:
        """Return summer/winter threshold temperature."""
        return self._suwi_threshold

    # Room influence
    @property
    def room_influence(self) -> float | None:
        """Return room influence percentage."""
        return self._room_influence

    # Mode properties
    @property
    def boost_mode(self) -> str | None:
        """Return boost mode status."""
        return self._boost_mode

    @property
    def operating_season(self) -> str | None:
        """Return operating season mode."""
        return self._operating_season

    @property
    def night_switch_mode(self) -> str | None:
        """Return night switch mode."""
        return self._night_switch_mode

    @property
    def suwi_switch_mode(self) -> str | None:
        """Return summer/winter switch mode."""
        return self._suwi_switch_mode

    # Boost properties
    @property
    def boost_duration(self) -> float | None:
        """Return boost duration in minutes."""
        return self._boost_duration

    @property
    def boost_temperature(self) -> float | None:
        """Return boost temperature."""
        return self._boost_temperature

    @property
    def boost_remaining_time(self) -> float | None:
        """Return boost remaining time in minutes."""
        return self._boost_remaining_time

    # Select properties
    @property
    def circuit_type(self) -> str | None:
        """Return heating circuit type."""
        return self._circuit_type

    @property
    def control(self) -> str | None:
        """Return control mode."""
        return self._control

    @property
    def building_heatup(self) -> str | None:
        """Return building heatup mode."""
        return self._building_heatup

    @property
    def setpoint_optimization(self) -> str | None:
        """Return setpoint optimization mode."""
        return self._setpoint_optimization

    async def initialize(self) -> bool:
        """Initialize heating circuit - fetch initial data.

        Returns:
            True if successful
        """
        try:
            await self.update()
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to initialize heating circuit %s: %s", self.hc_id, err)
            return False

    async def update(self) -> None:
        """Update heating circuit data from API."""
        try:
            # Fetch heating curve settings
            heat_curve_max_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/heatCurveMax")
            if heat_curve_max_data and "value" in heat_curve_max_data:
                self._heat_curve_max = float(heat_curve_max_data["value"])

            heat_curve_min_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/heatCurveMin")
            if heat_curve_min_data and "value" in heat_curve_min_data:
                self._heat_curve_min = float(heat_curve_min_data["value"])

            # Fetch supply temperature settings
            max_supply_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/maxSupply")
            if max_supply_data and "value" in max_supply_data:
                self._max_supply = float(max_supply_data["value"])

            min_supply_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/minSupply")
            if min_supply_data and "value" in min_supply_data:
                self._min_supply = float(min_supply_data["value"])

            supply_setpoint_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/supplyTemperatureSetpoint")
            if supply_setpoint_data and "value" in supply_setpoint_data:
                self._supply_temp_setpoint = float(supply_setpoint_data["value"])

            # Fetch other temperature settings
            min_outdoor_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/minOutdoorTemp")
            if min_outdoor_data and "value" in min_outdoor_data:
                self._min_outdoor_temp = float(min_outdoor_data["value"])

            night_threshold_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/nightThreshold")
            if night_threshold_data and "value" in night_threshold_data:
                self._night_threshold = float(night_threshold_data["value"])

            suwi_threshold_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/suWiThreshold")
            if suwi_threshold_data and "value" in suwi_threshold_data:
                self._suwi_threshold = float(suwi_threshold_data["value"])

            # Fetch room influence
            room_influence_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/roomInfluence")
            if room_influence_data and "value" in room_influence_data:
                self._room_influence = float(room_influence_data["value"])

            # Fetch mode settings
            boost_mode_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/boostMode")
            if boost_mode_data and "value" in boost_mode_data:
                self._boost_mode = boost_mode_data["value"]

            operating_season_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/operatingSeason")
            if operating_season_data and "value" in operating_season_data:
                self._operating_season = operating_season_data["value"]

            night_switch_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/nightSwitchMode")
            if night_switch_data and "value" in night_switch_data:
                self._night_switch_mode = night_switch_data["value"]

            suwi_switch_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/suWiSwitchMode")
            if suwi_switch_data and "value" in suwi_switch_data:
                self._suwi_switch_mode = suwi_switch_data["value"]

            # Fetch circuit type and control settings
            circuit_type_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/type")
            if circuit_type_data and "value" in circuit_type_data:
                self._circuit_type = circuit_type_data["value"]

            control_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/control")
            if control_data and "value" in control_data:
                self._control = control_data["value"]

            building_heatup_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/buildingHeatup")
            if building_heatup_data and "value" in building_heatup_data:
                self._building_heatup = building_heatup_data["value"]

            setpoint_opt_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/setpointOptimization")
            if setpoint_opt_data and "value" in setpoint_opt_data:
                self._setpoint_optimization = setpoint_opt_data["value"]

            # Fetch boost settings
            boost_duration_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/boostDuration")
            if boost_duration_data and "value" in boost_duration_data:
                self._boost_duration = float(boost_duration_data["value"])

            boost_temp_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/boostTemperature")
            if boost_temp_data and "value" in boost_temp_data:
                self._boost_temperature = float(boost_temp_data["value"])

            boost_remaining_data = await self._get_resource(f"/heatingCircuits/{self.hc_id}/boostRemainingTime")
            if boost_remaining_data and "value" in boost_remaining_data:
                self._boost_remaining_time = float(boost_remaining_data["value"])

            self._update_initialized = True

            _LOGGER.debug(
                "Updated heating circuit %s: curve_max=%s, curve_min=%s, max_supply=%s, min_supply=%s",
                self.hc_id,
                self._heat_curve_max,
                self._heat_curve_min,
                self._max_supply,
                self._min_supply,
            )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error updating heating circuit %s: %s", self.hc_id, err)
            # Don't raise - allow partial updates
