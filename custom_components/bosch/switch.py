"""Support for Bosch CT200 switch entities."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .bosch_entity import BoschEntity
from .const import (
    COORDINATOR,
    DOMAIN,
    GATEWAY,
    SWITCH,
    UUID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Bosch REST switch entities from a config entry."""
    uuid = config_entry.data[UUID]
    data = hass.data[DOMAIN][uuid]
    coordinator = data[COORDINATOR]
    gateway = data[GATEWAY]
    data_switch = []

    for config in (
        ("child_lock", "Child Lock", "mdi:lock"),
        ("away_mode", "Away Mode", "mdi:home-export-outline"),
        ("auto_away", "Auto Away", "mdi:home-automation"),
        ("window_detection", "Window Detection", "mdi:window-open-variant"),
        ("notification_light", "Notification Light", "mdi:lightbulb-on"),
    ):
        data_switch.append(
            RestSystemSwitch(
                coordinator=coordinator,
                hass=hass,
                uuid=uuid,
                gateway=gateway,
                switch_type=config[0],
                name_suffix=config[1],
                icon=config[2],
                is_enabled=True,
            )
        )

    for zone in gateway.zones:
        data_switch.append(
            RestZoneSwitch(
                coordinator=coordinator,
                hass=hass,
                uuid=uuid,
                zone=zone,
                gateway=gateway,
                switch_type="window_detection",
                name_suffix="Window Detection",
                icon="mdi:window-open-variant",
                is_enabled=True,
            )
        )

    data[SWITCH] = data_switch
    async_add_entities(data[SWITCH])
    return True


class RestSystemSwitch(CoordinatorEntity, BoschEntity, SwitchEntity):
    """REST system switch entity."""

    # API endpoint mapping for each switch type
    API_PATHS = {
        "child_lock": "/devices/device1/thermostat/childLock/enabled",
        "away_mode": "/system/awayMode/enabled",
        "auto_away": "/system/autoAway/enabled",
        "window_detection": "/system/openWindowDetection/enabled",
        "notification_light": "/gateway/notificationLight/enabled",
    }

    @classmethod
    def _state_from_cache(cls, gateway, switch_type: str) -> bool | None:
        """Return the current switch state from the cached system payload."""
        path = cls.API_PATHS.get(switch_type)
        if not path:
            return None
        data = gateway.system_cache.get(path)
        if data and "value" in data:
            return data["value"] == "true"
        return None

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        gateway,
        switch_type: str,
        name_suffix: str,
        icon: str,
        is_enabled: bool = True,
    ):
        """Initialize REST system switch entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._gateway_wrapper = gateway
        self._switch_type = switch_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._is_enabled = is_enabled
        self._state = self._state_from_cache(gateway, switch_type)

        # Generate unique ID
        self._attr_unique_id = f"{uuid}_system_{switch_type}"

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
        """Return unique device identifier - system switches go to main device."""
        return {(DOMAIN, self._uuid)}

    @property
    def enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        return self._is_enabled

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn on switch."""
        await self._set_state("true")

    async def async_turn_off(self, **kwargs):
        """Turn off switch."""
        await self._set_state("false")

    async def _set_state(self, value: str):
        """Set switch state via API."""
        try:
            # Get API path
            path = self.API_PATHS.get(self._switch_type)
            if not path:
                _LOGGER.error("Unknown switch type: %s", self._switch_type)
                return

            # Set value via API
            if hasattr(self._gateway_wrapper, 'client'):
                result = await self._gateway_wrapper.set_resource_value(path, value)

                if result:
                    # Update local state (will be confirmed by next poll)
                    self._state = value == "true"
                    await self.coordinator.async_request_refresh()
                    _LOGGER.info("Set system %s to %s", self._switch_type, value)
                else:
                    _LOGGER.error("Failed to set system %s", self._switch_type)

        except Exception as err:
            _LOGGER.error("Error setting system %s: %s", self._switch_type, err)

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._state = self._state_from_cache(
            self._gateway_wrapper, self._switch_type
        )
        self.async_write_ha_state()


class RestZoneSwitch(CoordinatorEntity, BoschEntity, SwitchEntity):
    """REST zone switch entity."""

    # API endpoint mapping for each switch type
    API_PATHS = {
        "window_detection": "/zones/{zone_id}/openWindowDetection/enabled",
    }

    def __init__(
        self,
        coordinator,
        hass,
        uuid,
        zone,
        gateway,
        switch_type: str,
        name_suffix: str,
        icon: str,
        is_enabled: bool = True,
    ):
        """Initialize REST zone switch entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._zone = zone
        self._switch_type = switch_type
        self._name_suffix = name_suffix
        self._attr_icon = icon
        self._is_enabled = is_enabled
        self._state = zone.window_detection_enabled

        # Generate unique ID
        self._attr_unique_id = f"{uuid}{zone.id}_{switch_type}"

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
    def enabled_default(self) -> bool:
        """Return if entity is enabled by default."""
        return self._is_enabled

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn on switch."""
        await self._set_state("on")

    async def async_turn_off(self, **kwargs):
        """Turn off switch."""
        await self._set_state("off")

    async def _set_state(self, value: str):
        """Set switch state via API."""
        try:
            # Get API path template and fill in zone_id
            path_template = self.API_PATHS.get(self._switch_type)
            if not path_template:
                _LOGGER.error("Unknown switch type: %s", self._switch_type)
                return

            path = path_template.format(zone_id=self._zone.zone_id)

            # Set value via API
            result = await self._zone.client.set_resource(path, value)

            if result:
                # Update local state
                self._state = value == "on"
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Set zone %s %s to %s", self._zone.zone_id, self._switch_type, value)
            else:
                _LOGGER.error("Failed to set zone %s %s", self._zone.zone_id, self._switch_type)

        except Exception as err:
            _LOGGER.error("Error setting zone %s %s: %s", self._zone.zone_id, self._switch_type, err)

    def _handle_coordinator_update(self):
        """Refresh the switch state from the zone wrapper."""
        self._state = self._zone.window_detection_enabled
        self.async_write_ha_state()
