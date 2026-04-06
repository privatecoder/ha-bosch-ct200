"""OAuth2 service handlers for the Bosch CT200 integration."""
from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse

from .const import (
    COORDINATOR,
    DOMAIN,
    ENTRY_ID,
    GATEWAY,
    SERVICE_GET,
    SERVICE_PUT_FLOAT,
    SERVICE_PUT_STRING,
    SERVICE_UPDATE,
    VALUE,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_INTEGRATION_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): cv.ensure_list})
SERVICE_GET_SCHEMA = SERVICE_INTEGRATION_SCHEMA.extend({vol.Required("path"): str})
SERVICE_PUT_STRING_SCHEMA = SERVICE_GET_SCHEMA.extend({vol.Required(VALUE): str})
SERVICE_PUT_FLOAT_SCHEMA = SERVICE_GET_SCHEMA.extend(
    {vol.Required(VALUE): vol.Or(int, float)}
)


def _resolve_entry_contexts(hass: HomeAssistant, device_ids: list[str]) -> list[dict]:
    """Resolve Bosch runtime contexts for the targeted Home Assistant devices."""
    registry = dr.async_get(hass)
    runtime_entries = hass.data.get(DOMAIN, {})
    resolved: list[dict] = []
    seen_entry_ids: set[str] = set()

    for target in device_ids:
        device = registry.async_get(target)
        if device is None:
            _LOGGER.warning("Device '%s' not found in device registry", target)
            continue

        for config_entry_id in device.config_entries:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry is None or config_entry.domain != DOMAIN:
                continue
            if config_entry.entry_id in seen_entry_ids:
                continue

            for context in runtime_entries.values():
                if context.get(ENTRY_ID) == config_entry.entry_id:
                    resolved.append(context)
                    seen_entry_ids.add(config_entry.entry_id)
                    break

    return resolved


def async_register_services(hass: HomeAssistant, entry) -> None:
    """Register CT200 OAuth2 services once for the domain."""

    del entry

    async def async_handle_refresh(service_call: ServiceCall) -> None:
        """Trigger a coordinator refresh for the selected integration devices."""
        contexts = _resolve_entry_contexts(hass, service_call.data[ATTR_DEVICE_ID])
        for context in contexts:
            await context[COORDINATOR].async_request_refresh()

    async def async_handle_get(service_call: ServiceCall) -> ServiceResponse:
        """Fetch an arbitrary PointT resource path."""
        contexts = _resolve_entry_contexts(hass, service_call.data[ATTR_DEVICE_ID])
        path = service_call.data["path"]
        data = []
        for context in contexts:
            payload = await context[GATEWAY].client.get_resource(path)
            data.append(payload)
        return {"data": data}

    async def async_handle_put(service_call: ServiceCall) -> None:
        """Write an arbitrary PointT resource path and refresh the model cache."""
        contexts = _resolve_entry_contexts(hass, service_call.data[ATTR_DEVICE_ID])
        path = service_call.data["path"]
        value = service_call.data[VALUE]

        for context in contexts:
            gateway = context[GATEWAY]
            if await gateway.set_resource_value(path, value):
                await context[COORDINATOR].async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE,
            async_handle_refresh,
            SERVICE_INTEGRATION_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_GET):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET,
            async_handle_get,
            schema=SERVICE_GET_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PUT_STRING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PUT_STRING,
            async_handle_put,
            SERVICE_PUT_STRING_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PUT_FLOAT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PUT_FLOAT,
            async_handle_put,
            SERVICE_PUT_FLOAT_SCHEMA,
        )


def async_remove_services(hass: HomeAssistant, entry) -> None:
    """Remove CT200 services once the last entry unloads."""

    del entry

    if hass.data.get(DOMAIN):
        return

    for service_name in (
        SERVICE_UPDATE,
        SERVICE_GET,
        SERVICE_PUT_STRING,
        SERVICE_PUT_FLOAT,
    ):
        hass.services.async_remove(DOMAIN, service_name)
