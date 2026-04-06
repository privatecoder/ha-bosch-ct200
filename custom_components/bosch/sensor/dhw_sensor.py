"""Support for Bosch REST DHW Circuit Sensors."""
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


class RestDhwSensor(CoordinatorEntity, BoschEntity, SensorEntity):
    """Representation of a REST DHW sensor."""

    # Sensor configuration mapping
    SENSOR_CONFIG = {
        "actual_temp": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
        },
        "hot_water_system": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
        "state": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
        "operation_mode": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
        "extra_dhw": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
        "thermal_disinfect_last_result": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
        "thermal_disinfect_state": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
        "thermal_disinfect_weekday": {
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        dhw,
        gateway,
        sensor_type: str,
        name_suffix: str,
        icon: str,
        is_enabled: bool = True,
    ):
        """Initialize the DHW sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        self._dhw = dhw
        self._sensor_type = sensor_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._is_enabled = is_enabled

        # Get sensor configuration
        config = self.SENSOR_CONFIG.get(sensor_type, {})
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{dhw.id}_{sensor_type}"

        super().__init__(
            hass=hass, uuid=uuid, bosch_object=dhw, gateway=gateway
        )

        # Set name
        self._name = name_suffix
        self._name_prefix = ""

    @property
    def device_name(self):
        """Return device name."""
        return self._dhw.name

    @property
    def _domain_identifier(self):
        """Return unique device identifier for this DHW circuit."""
        return {(DOMAIN, self._dhw.id, self._uuid)}

    @property
    def enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        return self._is_enabled

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if not self._dhw or not self._dhw.update_initialized:
            return None

        # Get value from DHW property
        value = getattr(self._dhw, self._sensor_type, None)
        return value
