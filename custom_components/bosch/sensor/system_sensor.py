"""Support for Bosch REST System Sensors (humidity, outdoor temp, etc)."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..bosch_entity import BoschEntity
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RestSystemSensor(CoordinatorEntity, BoschEntity, SensorEntity):
    """Representation of a REST system sensor."""

    # Sensor configuration mapping
    SENSOR_CONFIG = {
        "indoor_humidity": {
            "unit": PERCENTAGE,
            "device_class": SensorDeviceClass.HUMIDITY,
            "state_class": SensorStateClass.MEASUREMENT,
            "api_path": "/system/sensors/humidity/indoor_h1",
        },
        "outdoor_temperature": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "api_path": "/system/sensors/temperatures/outdoor_t1",
        },
        "indoor_air_temperature": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "api_path": "/system/sensors/temperatures/indoorAirDigital",
        },
        "indoor_chip_temperature": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "api_path": "/system/sensors/temperatures/indoorChip",
            "entity_category": EntityCategory.DIAGNOSTIC,
        },
        "indoor_pcb_temperature": {
            "unit": UnitOfTemperature.CELSIUS,
            "device_class": SensorDeviceClass.TEMPERATURE,
            "state_class": SensorStateClass.MEASUREMENT,
            "api_path": "/system/sensors/temperatures/indoorPCB",
            "entity_category": EntityCategory.DIAGNOSTIC,
        },
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        gateway,
        sensor_type: str,
        name_suffix: str,
        icon: str,
        is_enabled: bool = True,
    ) -> None:
        """Initialize the system sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        self._gateway_wrapper = gateway
        self._sensor_type = sensor_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._is_enabled = is_enabled
        self._value = None

        # Get sensor configuration
        config = self.SENSOR_CONFIG.get(sensor_type, {})
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")
        self._attr_entity_category = config.get("entity_category")
        self._api_path = config.get("api_path")

        # Generate unique ID
        self._attr_unique_id = f"{uuid}_system_{sensor_type}"

        # CoordinatorEntity is first in the MRO, so BoschEntity must be
        # initialized explicitly with the metadata context.
        BoschEntity.__init__(
            self, hass=hass, uuid=uuid, bosch_object=gateway, gateway=gateway
        )

        # Set name
        self._name = name_suffix
        self._name_prefix = ""

    @property
    def device_name(self):
        """Return device name."""
        return "Bosch CT200"

    @property
    def _domain_identifier(self):
        """Return unique device identifier - system sensors go to main device."""
        return {(DOMAIN, self._uuid)}

    @property
    def enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        return self._is_enabled

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._value

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        data = self._gateway_wrapper.get_cached_resource(self._api_path)
        if data and "value" in data:
            try:
                self._value = float(data["value"])
            except (ValueError, TypeError):
                self._value = None
        self.async_write_ha_state()
