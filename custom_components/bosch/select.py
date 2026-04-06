"""Support for Bosch CT200 select entities."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .bosch_entity import BoschEntity
from .const import (
    COORDINATOR,
    DOMAIN,
    GATEWAY,
    SELECT,
    UUID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Bosch REST select entities from a config entry."""
    uuid = config_entry.data[UUID]
    data = hass.data[DOMAIN][uuid]
    coordinator = data[COORDINATOR]
    gateway = data[GATEWAY]
    data[SELECT] = []

    for zone in gateway.zones:
        for config in (
            ("icon", "Icon", "mdi:image", ["living", "bedroom", "kitchen", "bathroom", "office", "others"]),
            ("heating_type", "Heating Type", "mdi:radiator", ["radiator", "convector", "floor"]),
        ):
            data[SELECT].append(
                RestZoneSelect(
                    coordinator=coordinator,
                    hass=hass,
                    uuid=uuid,
                    zone=zone,
                    gateway=gateway,
                    select_type=config[0],
                    name_suffix=config[1],
                    icon=config[2],
                    options=config[3],
                )
            )

    for heating_circuit in gateway.rest_heating_circuits:
        for config in (
            ("room_influence", "Room Influence", "mdi:home-thermometer", ["none", "low", "medium"]),
            ("circuit_type", "Circuit Type", "mdi:heating-coil", ["floor", "radiator", "convector"]),
            ("control", "Control Mode", "mdi:auto-mode", ["weather", "room", "outdoor"]),
            ("building_heatup", "Building Heatup", "mdi:home-thermometer-outline", ["slow", "normal", "fast"]),
            ("setpoint_optimization", "Setpoint Optimization", "mdi:tune", ["off", "auto"]),
        ):
            data[SELECT].append(
                RestHeatingCircuitSelect(
                    coordinator=coordinator,
                    hass=hass,
                    uuid=uuid,
                    hc=heating_circuit,
                    gateway=gateway,
                    select_type=config[0],
                    name_suffix=config[1],
                    icon=config[2],
                    options=config[3],
                )
            )

    data[SELECT].append(
        RestSystemSelect(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            gateway=gateway,
            select_type="pir_sensitivity",
            name_suffix="PIR Sensitivity",
            icon="mdi:motion-sensor",
            options=["low", "medium", "high"],
        )
    )

    # Gateway splash screen
    data[SELECT].append(
        RestSystemSelect(
            coordinator=coordinator,
            hass=hass,
            uuid=uuid,
            gateway=gateway,
            select_type="splash_screen",
            name_suffix="Splash Screen",
            icon="mdi:monitor-dashboard",
            options=["weather", "clock", "none"],
        )
    )

    async_add_entities(data[SELECT])
    return True


class RestZoneSelect(CoordinatorEntity, BoschEntity, SelectEntity):
    """REST zone select control entity."""

    # API endpoint mapping for each select type
    API_PATHS = {
        "icon": "/zones/{zone_id}/icon",
        "heating_type": "/zones/{zone_id}/heatingType",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        zone,
        gateway,
        select_type: str,
        name_suffix: str,
        icon: str,
        options: list[str],
    ):
        """Initialize REST zone select entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._zone = zone
        self._select_type = select_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_options = options

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{zone.id}_{select_type}"

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
    def current_option(self) -> str | None:
        """Return current selected option."""
        if not self._zone or not self._zone.update_initialized:
            return None

        # Get value from zone property
        value = getattr(self._zone, self._select_type, None)
        _LOGGER.debug("RestZoneSelect.current_option: %s = %s (type: %s)", self._select_type, value, type(value).__name__)
        return str(value) if value is not None else None

    @property
    def options(self) -> list[str]:
        """Return list of available options."""
        return self._attr_options

    async def async_select_option(self, option: str) -> None:
        """Set new option via API."""
        try:
            # Get API path template and fill in zone_id
            path_template = self.API_PATHS.get(self._select_type)
            if not path_template:
                _LOGGER.error("Unknown select type: %s", self._select_type)
                return

            path = path_template.format(zone_id=self._zone.zone_id)

            _LOGGER.info("RestZoneSelect: Setting %s to '%s' via %s", self._select_type, option, path)

            # Set value via API
            result = await self._zone.client.set_resource(path, option)

            _LOGGER.info("RestZoneSelect: API set_resource returned: %s", result)

            if result:
                # Update local state
                setattr(self._zone, f"_{self._select_type}", option)
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Set %s for %s to '%s'", self._select_type, self._zone.zone_id, option)
            else:
                _LOGGER.error("Failed to set %s for %s to '%s' (API returned False/None)",
                            self._select_type, self._zone.zone_id, option)

        except Exception as err:
            _LOGGER.error("Error setting %s for %s to '%s': %s",
                        self._select_type, self._zone.zone_id, option, err, exc_info=True)

class RestHeatingCircuitSelect(CoordinatorEntity, BoschEntity, SelectEntity):
    """REST heating circuit select control entity."""

    # API endpoint mapping for each select type
    API_PATHS = {
        "room_influence": "/heatingCircuits/{hc_id}/roomInfluence",
        "circuit_type": "/heatingCircuits/{hc_id}/type",
        "control": "/heatingCircuits/{hc_id}/control",
        "building_heatup": "/heatingCircuits/{hc_id}/buildingHeatup",
        "setpoint_optimization": "/heatingCircuits/{hc_id}/setpointOptimization",
    }

    # Value mapping for room_influence (UI option -> API value)
    # API accepts floatValue with range 0.0-2.0, step 1.0
    ROOM_INFLUENCE_MAP = {
        "none": 0.0,
        "low": 1.0,
        "medium": 2.0,
    }

    # Reverse mapping (API value -> UI option)
    ROOM_INFLUENCE_REVERSE_MAP = {
        0.0: "none",
        1.0: "low",
        2.0: "medium",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        hc,
        gateway,
        select_type: str,
        name_suffix: str,
        icon: str,
        options: list[str],
    ):
        """Initialize REST heating circuit select entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._hc = hc
        self._select_type = select_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_options = options

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{hc.id}_{select_type}"

        BoschEntity.__init__(
            self, hass=hass, uuid=uuid, bosch_object=hc, gateway=gateway
        )

        # Set name
        self._name = f"{hc.name} {name_suffix}"
        self._name_prefix = ""  # No prefix

    @property
    def device_name(self):
        """Return device name."""
        return f"{self._name_prefix}{self._hc.name}"

    @property
    def _domain_identifier(self):
        """Return unique device identifier for this heating circuit."""
        return {(DOMAIN, self._hc.id, self._uuid)}

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        if not self._hc or not self._hc.update_initialized:
            return None

        # Get numeric value from HC property
        value = getattr(self._hc, self._select_type, None)
        if value is None:
            return None

        # Convert numeric value to option string
        if self._select_type == "room_influence":
            return self.ROOM_INFLUENCE_REVERSE_MAP.get(float(value), "none")

        return str(value)

    @property
    def options(self) -> list[str]:
        """Return list of available options."""
        return self._attr_options

    async def async_select_option(self, option: str) -> None:
        """Set new option via API."""
        try:
            # Get API path template and fill in hc_id
            path_template = self.API_PATHS.get(self._select_type)
            if not path_template:
                _LOGGER.error("Unknown select type: %s", self._select_type)
                return

            path = path_template.format(hc_id=self._hc.hc_id)

            # Convert option string to numeric value if needed
            if self._select_type == "room_influence":
                api_value = self.ROOM_INFLUENCE_MAP.get(option, 0)
            else:
                api_value = option

            # Set value via API
            result = await self._hc.client.set_resource(path, api_value)

            if result:
                # Update local state
                setattr(self._hc, f"_{self._select_type}", api_value)
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Set %s for %s to %s (%s)", self._select_type, self._hc.hc_id, option, api_value)
            else:
                _LOGGER.error("Failed to set %s for %s", self._select_type, self._hc.hc_id)

        except Exception as err:
            _LOGGER.error("Error setting %s for %s: %s", self._select_type, self._hc.hc_id, err)

class RestSystemSelect(CoordinatorEntity, BoschEntity, SelectEntity):
    """REST system select entity."""

    # API endpoint mapping for each select type
    API_PATHS = {
        "pir_sensitivity": "/gateway/pirSensitivity",
        "splash_screen": "/gateway/ui/splashScreen",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        gateway,
        select_type: str,
        name_suffix: str,
        icon: str,
        options: list[str],
    ):
        """Initialize REST system select entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._gateway_wrapper = gateway
        self._select_type = select_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._attr_options = options
        self._value = None

        # Generate unique ID
        self._attr_unique_id = f"{uuid}_system_{select_type}"

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
        """Return unique device identifier - system selects go to main device."""
        return {(DOMAIN, self._uuid)}

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        return self._value

    @property
    def options(self) -> list[str]:
        """Return list of available options."""
        return self._attr_options

    async def async_select_option(self, option: str) -> None:
        """Set new option via API."""
        try:
            # Get API path
            path = self.API_PATHS.get(self._select_type)
            if not path:
                _LOGGER.error("Unknown select type: %s", self._select_type)
                return

            # Set value via API
            if hasattr(self._gateway_wrapper, 'client'):
                result = await self._gateway_wrapper.set_resource_value(path, option)

                if result:
                    # Update local state (will be confirmed by next poll)
                    self._value = option
                    await self.coordinator.async_request_refresh()
                    _LOGGER.info("Set system %s to %s", self._select_type, option)
                else:
                    _LOGGER.error("Failed to set system %s", self._select_type)

        except Exception as err:
            _LOGGER.error("Error setting system %s: %s", self._select_type, err)

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        path = self.API_PATHS.get(self._select_type)
        if not path:
            return
        cache = self._gateway_wrapper.system_cache
        data = cache.get(path)
        if data and "value" in data:
            self._value = str(data["value"])
        self.async_write_ha_state()
