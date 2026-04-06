"""Support for Bosch REST Heating Circuit Sensors."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..bosch_entity import BoschEntity
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RestHeatingCircuitSensor(CoordinatorEntity, BoschEntity, SensorEntity):
    """Representation of a REST heating circuit sensor."""

    # Sensor configuration mapping
    SENSOR_CONFIG = {
        "supply_temp_setpoint": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "min_outdoor_temp": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "night_threshold": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "suwi_threshold": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "boost_remaining_time": {
            "unit": "min",
            "device_class": SensorDeviceClass.DURATION,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "operating_season": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "string",
        },
        "boost_mode": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "string",
        },
        "night_switch_mode": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "string",
        },
        "suwi_switch_mode": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "string",
        },
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        hc,  # RestHeatingCircuit instance
        gateway,
        sensor_type: str,
        name_suffix: str,
        icon: str,
        is_enabled: bool = True,
    ) -> None:
        """Initialize the sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        self._hc = hc
        self._sensor_type = sensor_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._is_enabled = is_enabled

        # Get sensor configuration
        config = self.SENSOR_CONFIG.get(sensor_type, {})
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")
        self._format = config.get("format", "number")

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{hc.id}_{sensor_type}"

        # Use the wrapped circuit object for device metadata and state access.
        super().__init__(
            hass=hass, uuid=uuid, bosch_object=hc, gateway=gateway
        )

        # Set name
        self._name = f"{hc.name} {name_suffix}"
        self._name_prefix = ""

    @property
    def device_name(self):
        """Return name displayed in device_info."""
        return f"{self._name_prefix}{self._hc.name}"

    @property
    def _domain_identifier(self):
        """Return unique device identifier for this heating circuit."""
        return {(DOMAIN, self._hc.id, self._uuid)}

    @property
    def enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        return self._is_enabled

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if not self._hc or not self._hc.update_initialized:
            return None

        # Get value from heating circuit
        value = getattr(self._hc, self._sensor_type, None)

        # Format value based on type
        if value is None:
            return None

        if self._format == "number":
            return value
        elif self._format == "string":
            return str(value) if value is not None else None

        return value
