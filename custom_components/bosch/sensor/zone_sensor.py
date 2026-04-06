"""Support for Bosch REST Zone Sensors."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..bosch_entity import BoschEntity
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RestZoneSensor(CoordinatorEntity, BoschEntity, SensorEntity):
    """Representation of a REST zone sensor."""

    # Sensor configuration mapping
    SENSOR_CONFIG = {
        "valve_position": {
            "unit": PERCENTAGE,
            "device_class": None,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "next_setpoint_temp": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "time_to_next_setpoint": {
            "unit": UnitOfTime.MINUTES,
            "device_class": SensorDeviceClass.DURATION,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
        "optimum_start_active": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "active_inactive",
        },
        "window_detection_enabled": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "enabled_disabled",
        },
        "window_open": {
            "unit": None,
            "device_class": None,
            "state_class": None,
            "format": "open_closed",
        },
        "optimum_start_heatup_rate": {
            "unit": "s/K",
            "device_class": None,
            "state_class": SensorStateClass.MEASUREMENT,
            "format": "number",
        },
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        zone,  # RestZone instance
        gateway,
        sensor_type: str,
        name_suffix: str,
        icon: str,
        is_enabled: bool = True,
    ) -> None:
        """Initialize the sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        self._zone = zone
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
        self._attr_unique_id = f"{uuid}{zone.id}_{sensor_type}"

        # Use the wrapped zone object for device metadata and state access.
        super().__init__(
            hass=hass, uuid=uuid, bosch_object=zone, gateway=gateway
        )

        # Set name
        self._name = name_suffix
        self._name_prefix = ""

    @property
    def device_name(self):
        """Return name displayed in device_info."""
        return f"{self._name_prefix}{self._zone.name}"

    @property
    def _domain_identifier(self):
        """Return unique device identifier for this zone."""
        return {(DOMAIN, self._zone.id, self._uuid)}

    @property
    def enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        return self._is_enabled

    @property
    def native_value(self) -> str | float | None:
        """Return the state of the sensor."""
        if not self._zone or not self._zone.update_initialized:
            return None

        # Get value from zone
        value = getattr(self._zone, self._sensor_type, None)

        # Format value based on type
        if value is None:
            return None

        if self._format == "number":
            return value
        elif self._format == "active_inactive":
            return "Active" if value else "Inactive"
        elif self._format == "enabled_disabled":
            return "Enabled" if value else "Disabled"
        elif self._format == "open_closed":
            return "Open" if value else "Closed"

        return value
