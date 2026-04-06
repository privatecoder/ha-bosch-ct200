"""Tests for Bosch CT200 switch entities."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.bosch.switch import RestSystemSwitch, RestZoneSwitch


def _make_gateway():
    return SimpleNamespace(
        device_model="Bosch",
        device_type="CT200 (EasyControl)",
        firmware="05.04.00",
        system_cache={},
    )


def _make_zone(window_detection_enabled):
    return SimpleNamespace(
        id="zn1",
        zone_id="zn1",
        name="Zone zn1",
        window_detection_enabled=window_detection_enabled,
    )


def test_zone_switch_initializes_from_zone_state():
    """Zone switch should expose the known zone state immediately."""
    switch = RestZoneSwitch(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        zone=_make_zone(True),
        gateway=_make_gateway(),
        switch_type="window_detection",
        name_suffix="Window Detection",
        icon="mdi:window-open-variant",
    )

    assert switch.is_on is True


def test_zone_switch_updates_from_coordinator_data():
    """Zone switch should mirror the current zone-enabled flag on refresh."""
    zone = _make_zone(True)
    switch = RestZoneSwitch(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        zone=zone,
        gateway=_make_gateway(),
        switch_type="window_detection",
        name_suffix="Window Detection",
        icon="mdi:window-open-variant",
    )
    switch.async_write_ha_state = MagicMock()

    zone.window_detection_enabled = False
    switch._handle_coordinator_update()

    assert switch.is_on is False
    switch.async_write_ha_state.assert_called_once()


def test_system_switch_initializes_from_gateway_cache():
    """System switch should expose the cached state immediately."""
    gateway = _make_gateway()
    gateway.system_cache = {
        "/system/awayMode/enabled": {"value": "true"},
    }
    switch = RestSystemSwitch(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        gateway=gateway,
        switch_type="away_mode",
        name_suffix="Away Mode",
        icon="mdi:home-export-outline",
    )

    assert switch.is_on is True


def test_system_switch_updates_from_coordinator_data():
    """System switch should mirror the current cache value on refresh."""
    gateway = _make_gateway()
    gateway.system_cache = {
        "/system/awayMode/enabled": {"value": "true"},
    }
    switch = RestSystemSwitch(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        gateway=gateway,
        switch_type="away_mode",
        name_suffix="Away Mode",
        icon="mdi:home-export-outline",
    )
    switch.async_write_ha_state = MagicMock()

    gateway.system_cache["/system/awayMode/enabled"] = {"value": "false"}
    switch._handle_coordinator_update()

    assert switch.is_on is False
    switch.async_write_ha_state.assert_called_once()
