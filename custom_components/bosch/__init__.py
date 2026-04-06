"""Bosch CT200 integration setup."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ACCESS_TOKEN,
    CLIMATE,
    COORDINATOR,
    DEVICE_ID,
    DOMAIN,
    ENTRY_ID,
    GATEWAY,
    NUMBER,
    REFRESH_TOKEN,
    SCAN_INTERVAL,
    SELECT,
    SENSOR,
    SWITCH,
    UUID,
)
from .pointt_rest_client import PointTRestClient
from .rest_gateway_wrapper import RestGatewayWrapper
from .services import async_register_services, async_remove_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [CLIMATE, SENSOR, NUMBER, SELECT, SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize the Bosch integration domain."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Bosch CT200 config entry."""
    uuid = entry.data[UUID]
    device_id = entry.data[DEVICE_ID]
    domain_data = hass.data.setdefault(DOMAIN, {})

    _LOGGER.info("Setting up Bosch CT200 OAuth2 device %s", device_id)

    async def update_tokens(access_token: str, refresh_token: str) -> None:
        """Persist refreshed OAuth2 tokens."""
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                ACCESS_TOKEN: access_token,
                REFRESH_TOKEN: refresh_token,
            },
        )

    client = PointTRestClient(
        session=async_get_clientsession(hass),
        device_id=device_id,
        access_token=entry.data[ACCESS_TOKEN],
        refresh_token=entry.data[REFRESH_TOKEN],
        token_update_callback=update_tokens,
    )
    gateway = RestGatewayWrapper(client=client, entry=entry)

    try:
        if not await gateway.initialize():
            raise ConfigEntryNotReady("Failed to initialize Bosch OAuth2 gateway")
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.error("Error initializing Bosch OAuth2 gateway: %s", err)
        raise ConfigEntryNotReady("Failed to initialize Bosch OAuth2 gateway") from err

    async def _async_update_data() -> None:
        """Refresh the REST gateway state."""
        try:
            await gateway.update()
        except Exception as err:
            raise UpdateFailed(f"Error updating gateway: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"bosch_ct200_{device_id}",
        update_method=_async_update_data,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    domain_data[uuid] = {
        ENTRY_ID: entry.entry_id,
        GATEWAY: gateway,
        COORDINATOR: coordinator,
    }

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, uuid)},
        manufacturer="Bosch",
        model="CT200",
        name=gateway.device_name or f"Bosch CT200 ({device_id})",
        sw_version=gateway.firmware,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Bosch CT200 config entry."""
    uuid = entry.data[UUID]
    domain_data = hass.data.get(DOMAIN, {})
    data = domain_data.get(uuid, {})

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    gateway = data.get(GATEWAY)
    if gateway is not None and hasattr(gateway, "close"):
        await gateway.close()

    domain_data.pop(uuid, None)
    async_remove_services(hass, entry)
    return unload_ok
