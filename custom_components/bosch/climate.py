"""Support for Bosch Thermostat Climate."""
from __future__ import annotations

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACAction,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CLIMATE,
    COORDINATOR,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    GATEWAY,
    UUID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Bosch thermostat from a config entry."""
    uuid = config_entry.data[UUID]
    data = hass.data[DOMAIN][uuid]
    coordinator = data[COORDINATOR]
    gateway = data[GATEWAY]
    data[CLIMATE] = [
        RestBoschThermostat(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            bosch_object=heating_circuit,
            gateway=gateway,
        )
        for heating_circuit in gateway.heating_circuits
    ]
    async_add_entities(data[CLIMATE])
    return True


class RestBoschThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a Bosch thermostat for the OAuth2 (REST) path."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, hass, uuid, bosch_object, gateway) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator)
        self.hass = hass
        self._uuid = uuid
        self._bosch_object = bosch_object
        self._gateway = gateway
        self._name_prefix = (
            "Zone " if "/zones" in bosch_object.attr_id else "Heating circuit "
        )
        self._attr_unique_id = f"{uuid}{bosch_object.id}"
        self._attr_name = f"{self._name_prefix}{bosch_object.name}"
        # Initialise state from the bosch_object so the entity is ready before
        # the first coordinator refresh.
        self._temperature_unit = UnitOfTemperature.CELSIUS
        self._current_temperature = bosch_object.current_temp
        self._target_temperature = bosch_object.target_temperature
        self._hvac_modes = bosch_object.ha_modes
        self._hvac_mode = bosch_object.ha_mode
        self._state = bosch_object.state

    # ------------------------------------------------------------------
    # Device information
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        """Get attributes about the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._bosch_object.id, self._uuid)},
            manufacturer=self._gateway.device_model,
            model=self._gateway.device_type,
            name=self._bosch_object.device_name,
            sw_version=self._gateway.firmware,
            hw_version=self._uuid,
            via_device=(DOMAIN, self._uuid),
        )

    # ------------------------------------------------------------------
    # Temperature / unit properties
    # ------------------------------------------------------------------

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._temperature_unit

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return (
            self._bosch_object.min_temp
            if self._bosch_object.min_temp
            else DEFAULT_MIN_TEMP
        )

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return (
            self._bosch_object.max_temp
            if self._bosch_object.max_temp
            else DEFAULT_MAX_TEMP
        )

    # ------------------------------------------------------------------
    # HVAC / preset properties
    # ------------------------------------------------------------------

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE | (
            ClimateEntityFeature.PRESET_MODE
            if self._bosch_object.support_presets
            else 0
        )

    @property
    def hvac_mode(self):
        """Return current operation mode."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        hvac_action = self._bosch_object.hvac_action
        if hvac_action == HVACAction.HEATING:
            return HVACAction.HEATING
        if hvac_action in {HVACAction.IDLE, HVACMode.OFF}:
            return HVACAction.IDLE

    @property
    def hvac_modes(self) -> list:
        """List of available operation modes."""
        return self._hvac_modes

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return self._bosch_object.preset_modes

    @property
    def preset_mode(self):
        """Return current preset mode."""
        return self._bosch_object.preset_mode

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        _LOGGER.debug("Setting operation mode %s.", hvac_mode)
        await self._bosch_object.set_ha_mode(hvac_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("Setting target temperature %s.", temperature)
        await self._bosch_object.set_temperature(temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        await self._bosch_object.set_preset_mode(preset_mode)
        await self.coordinator.async_request_refresh()

    # ------------------------------------------------------------------
    # Coordinator update handler
    # ------------------------------------------------------------------

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._temperature_unit = UnitOfTemperature.CELSIUS
        self._current_temperature = self._bosch_object.current_temp
        self._target_temperature = self._bosch_object.target_temperature
        self._hvac_modes = self._bosch_object.ha_modes
        self._hvac_mode = self._bosch_object.ha_mode
        self._state = self._bosch_object.state
        self.async_write_ha_state()
