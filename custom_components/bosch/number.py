"""Bosch Thermostat Number Entities."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.components.number.const import NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .bosch_entity import BoschEntity
from .const import (
    COORDINATOR,
    DOMAIN,
    GATEWAY,
    NUMBER,
    UUID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Bosch REST number entities from a config entry."""
    uuid = config_entry.data[UUID]
    data = hass.data[DOMAIN][uuid]
    coordinator = data[COORDINATOR]
    gateway = data[GATEWAY]
    data_number = []
    for zone in gateway.zones:
        for config in (
            ("manual_temp_heating", "Manual Setpoint", "mdi:thermometer", 5.0, 30.0, 0.5, "°C"),
            ("clock_program", "Program", "mdi:clock-outline", 0.0, 24.0, 1.0, None),
            (
                "clock_override_temp",
                "Override Temperature",
                "mdi:thermometer-auto",
                0.0,
                30.0,
                0.5,
                "°C",
            ),
        ):
            data_number.append(
                RestZoneNumber(
                    coordinator=coordinator,
                    hass=hass,
                    uuid=uuid,
                    zone=zone,
                    gateway=gateway,
                    number_type=config[0],
                    name_suffix=config[1],
                    icon=config[2],
                    min_value=config[3],
                    max_value=config[4],
                    step=config[5],
                    unit=config[6],
                )
            )

    for heating_circuit in gateway.rest_heating_circuits:
        for config in (
            ("heat_curve_max", "Heating Curve Max", "mdi:chart-bell-curve", 25.0, 60.0, 1.0, "°C"),
            ("heat_curve_min", "Heating Curve Min", "mdi:chart-bell-curve", 20.0, 60.0, 1.0, "°C"),
            ("max_supply", "Max Supply Temp", "mdi:thermometer-high", 25.0, 60.0, 1.0, "°C"),
            ("min_supply", "Min Supply Temp", "mdi:thermometer-low", 10.0, 60.0, 1.0, "°C"),
            ("boost_duration", "Boost Duration", "mdi:timer", 1.0, 8.0, 1.0, "h"),
            ("boost_temperature", "Boost Temperature", "mdi:thermometer-plus", 5.0, 30.0, 0.5, "°C"),
        ):
            data_number.append(
                RestHeatingCircuitNumber(
                    coordinator=coordinator,
                    hass=hass,
                    uuid=uuid,
                    hc=heating_circuit,
                    gateway=gateway,
                    number_type=config[0],
                    name_suffix=config[1],
                    icon=config[2],
                    min_value=config[3],
                    max_value=config[4],
                    step=config[5],
                    unit=config[6],
                )
            )

    data_number.append(
        RestSystemNumber(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            gateway=gateway,
            number_type="temperature_offset",
            name_suffix="Temperature Offset",
            icon="mdi:thermometer-chevron-up",
            min_value=-2.0,
            max_value=2.0,
            step=0.5,
            unit="°C",
        )
    )

    for dhw in gateway.dhw_circuits:
        data_number.append(
            RestDhwNumber(
                coordinator=coordinator,
                hass=hass,
                uuid=uuid,
                dhw=dhw,
                gateway=gateway,
                number_type="extra_dhw_duration",
                name_suffix="Extra DHW Duration",
                icon="mdi:timer-outline",
                min_value=1.0,
                max_value=1440.0,
                step=1.0,
                unit="min",
            )
        )
        data_number.append(
            RestDhwNumber(
                coordinator=coordinator,
                hass=hass,
                uuid=uuid,
                dhw=dhw,
                gateway=gateway,
                number_type="temp_high",
                name_suffix="High Temperature",
                icon="mdi:thermometer-high",
                min_value=30.0,
                max_value=80.0,
                step=0.5,
                unit="°C",
            )
        )
        data_number.append(
            RestDhwNumber(
                coordinator=coordinator,
                hass=hass,
                uuid=uuid,
                dhw=dhw,
                gateway=gateway,
                number_type="thermal_disinfect_time",
                name_suffix="Thermal Disinfect Time",
                icon="mdi:timer-cog-outline",
                min_value=0.0,
                max_value=1439.0,
                step=1.0,
                unit="min",
            )
        )

    # Away mode temperature
    data_number.append(
        RestSystemNumber(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            gateway=gateway,
            number_type="away_temperature",
            name_suffix="Away Mode Temperature",
            icon="mdi:home-thermometer-outline",
            min_value=5.0,
            max_value=30.0,
            step=0.5,
            unit="°C",
        )
    )

    # Open window detection duration
    data_number.append(
        RestSystemNumber(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            gateway=gateway,
            number_type="window_detection_duration",
            name_suffix="Window Detection Duration",
            icon="mdi:timer-outline",
            min_value=5.0,
            max_value=60.0,
            step=5.0,
            unit="min",
        )
    )

    # Open window detection temperature
    data_number.append(
        RestSystemNumber(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            gateway=gateway,
            number_type="window_detection_temperature",
            name_suffix="Window Detection Temperature",
            icon="mdi:thermometer-alert",
            min_value=5.0,
            max_value=30.0,
            step=0.5,
            unit="°C",
        )
    )

    data[NUMBER] = data_number
    async_add_entities(data[NUMBER])
    return True


class RestZoneNumber(CoordinatorEntity, BoschEntity, NumberEntity):
    """REST zone number control entity."""
    _attr_mode: NumberMode = NumberMode.BOX

    # API endpoint mapping for each number type
    API_PATHS = {
        "manual_temp_heating": "/zones/{zone_id}/manualTemperatureHeating",
        "clock_program": "/zones/{zone_id}/clockProgram",
        "clock_override_temp": "/zones/{zone_id}/clockOverride/temperatureHeating",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        zone,
        gateway,
        number_type: str,
        name_suffix: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None,
    ):
        """Initialize REST zone number entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._zone = zone
        self._number_type = number_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{zone.id}_{number_type}"

        BoschEntity.__init__(
            self, hass=hass, uuid=uuid, bosch_object=zone, gateway=gateway
        )

        # Set name
        self._name = name_suffix
        self._name_prefix = ""

    @property
    def device_name(self):
        """Return device name."""
        return f"{self._name_prefix}{self._zone.name}"

    @property
    def _domain_identifier(self):
        """Return unique device identifier for this zone."""
        return {(DOMAIN, self._zone.id, self._uuid)}

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        if not self._zone or not self._zone.update_initialized:
            return None

        # Get value from zone property
        value = getattr(self._zone, self._number_type, None)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value via API."""
        try:
            # Get API path template and fill in zone_id
            path_template = self.API_PATHS.get(self._number_type)
            if not path_template:
                _LOGGER.error("Unknown number type: %s", self._number_type)
                return

            path = path_template.format(zone_id=self._zone.zone_id)

            # Set value via API
            result = await self._zone.client.set_resource(path, value)

            if result:
                # Update local state
                setattr(self._zone, f"_{self._number_type}", value)
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Set %s for %s to %s", self._number_type, self._zone.zone_id, value)
            else:
                _LOGGER.error("Failed to set %s for %s", self._number_type, self._zone.zone_id)

        except Exception as err:
            _LOGGER.error("Error setting %s for %s: %s", self._number_type, self._zone.zone_id, err)


class RestHeatingCircuitNumber(CoordinatorEntity, BoschEntity, NumberEntity):
    """REST heating circuit number control entity."""
    _attr_mode: NumberMode = NumberMode.BOX

    # API endpoint mapping for each number type
    API_PATHS = {
        "heat_curve_max": "/heatingCircuits/{hc_id}/heatCurveMax",
        "heat_curve_min": "/heatingCircuits/{hc_id}/heatCurveMin",
        "max_supply": "/heatingCircuits/{hc_id}/maxSupply",
        "min_supply": "/heatingCircuits/{hc_id}/minSupply",
        "boost_duration": "/heatingCircuits/{hc_id}/boostDuration",
        "boost_temperature": "/heatingCircuits/{hc_id}/boostTemperature",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        hc,
        gateway,
        number_type: str,
        name_suffix: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None,
    ):
        """Initialize REST heating circuit number entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._hc = hc
        self._number_type = number_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{hc.id}_{number_type}"

        BoschEntity.__init__(
            self, hass=hass, uuid=uuid, bosch_object=hc, gateway=gateway
        )

        # Set name
        self._name = f"{hc.name} {name_suffix}"
        self._name_prefix = ""  # No prefix - HC name already contains "Heating Circuit"

    @property
    def device_name(self):
        """Return device name."""
        return f"{self._name_prefix}{self._hc.name}"

    @property
    def _domain_identifier(self):
        """Return unique device identifier for this heating circuit."""
        return {(DOMAIN, self._hc.id, self._uuid)}

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        if not self._hc or not self._hc.update_initialized:
            return None

        # Get value from HC property
        value = getattr(self._hc, self._number_type, None)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value via API."""
        try:
            # Get API path template and fill in hc_id
            path_template = self.API_PATHS.get(self._number_type)
            if not path_template:
                _LOGGER.error("Unknown number type: %s", self._number_type)
                return

            path = path_template.format(hc_id=self._hc.hc_id)

            # Set value via API
            result = await self._hc.client.set_resource(path, value)

            if result:
                # Update local state
                setattr(self._hc, f"_{self._number_type}", value)
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Set %s for %s to %s", self._number_type, self._hc.hc_id, value)
            else:
                _LOGGER.error("Failed to set %s for %s", self._number_type, self._hc.hc_id)

        except Exception as err:
            _LOGGER.error("Error setting %s for %s: %s", self._number_type, self._hc.hc_id, err)


class RestSystemNumber(CoordinatorEntity, BoschEntity, NumberEntity):
    """REST system number control entity."""
    _attr_mode: NumberMode = NumberMode.BOX

    # API endpoint mapping for each number type
    API_PATHS = {
        "temperature_offset": "/system/sensors/temperatures/offset",
        "away_temperature": "/system/awayMode/temperature",
        "window_detection_duration": "/system/openWindowDetection/duration",
        "window_detection_temperature": "/system/openWindowDetection/temperature",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        gateway,
        number_type: str,
        name_suffix: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None,
    ):
        """Initialize REST system number entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._gateway_wrapper = gateway
        self._number_type = number_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._value = None

        # Generate unique ID
        self._attr_unique_id = f"{uuid}_system_{number_type}"

        # Use gateway wrapper as bosch_object
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
        """Return unique device identifier - system numbers go to main device."""
        return {(DOMAIN, self._uuid)}

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value via API."""
        try:
            # Get API path
            path = self.API_PATHS.get(self._number_type)
            if not path:
                _LOGGER.error("Unknown number type: %s", self._number_type)
                return

            # Set value via API
            if hasattr(self._gateway_wrapper, 'client'):
                result = await self._gateway_wrapper.set_resource_value(path, value)

                if result:
                    # Update local state (will be confirmed by next poll)
                    self._value = value
                    await self.coordinator.async_request_refresh()
                    _LOGGER.info("Set system %s to %s", self._number_type, value)
                else:
                    _LOGGER.error("Failed to set system %s", self._number_type)

        except Exception as err:
            _LOGGER.error("Error setting system %s: %s", self._number_type, err)

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        path = self.API_PATHS.get(self._number_type)
        if not path:
            return
        cache = self._gateway_wrapper.system_cache
        data = cache.get(path)
        if data and "value" in data:
            try:
                self._value = float(data["value"])
            except (ValueError, TypeError):
                pass
        self.async_write_ha_state()


class RestDhwNumber(CoordinatorEntity, BoschEntity, NumberEntity):
    """REST DHW number control entity."""
    _attr_mode: NumberMode = NumberMode.BOX

    # API endpoint mapping for each number type
    API_PATHS = {
        "extra_dhw_duration": "/dhwCircuits/{dhw_id}/extraDhwDuration",
        "temp_high": "/dhwCircuits/{dhw_id}/temperatureLevels/high",
        "thermal_disinfect_time": "/dhwCircuits/{dhw_id}/thermalDisinfect/time",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        dhw,
        gateway,
        number_type: str,
        name_suffix: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None,
    ):
        """Initialize REST DHW number entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._dhw = dhw
        self._number_type = number_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{dhw.id}_{number_type}"

        BoschEntity.__init__(
            self, hass=hass, uuid=uuid, bosch_object=dhw, gateway=gateway
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
    def native_value(self) -> float | None:
        """Return current value."""
        if not self._dhw or not self._dhw.update_initialized:
            return None

        # Get value from DHW property
        value = getattr(self._dhw, self._number_type, None)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value via API."""
        try:
            # Get API path template and fill in dhw_id
            path_template = self.API_PATHS.get(self._number_type)
            if not path_template:
                _LOGGER.error("Unknown number type: %s", self._number_type)
                return

            path = path_template.format(dhw_id=self._dhw.dhw_id)

            # Set value via API
            result = await self._dhw.client.set_resource(path, value)

            if result:
                # Update local state
                setattr(self._dhw, f"_{self._number_type}", value)
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Set %s for %s to %s", self._number_type, self._dhw.dhw_id, value)
            else:
                _LOGGER.error("Failed to set %s for %s", self._number_type, self._dhw.dhw_id)

        except Exception as err:
            _LOGGER.error("Error setting %s for %s: %s", self._number_type, self._dhw.dhw_id, err)
