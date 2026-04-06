"""Tests for Bosch CT200 device naming."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.bosch.climate import RestBoschThermostat
from custom_components.bosch.number import RestSystemNumber
from custom_components.bosch.rest_dhw_circuit import RestDhwCircuit
from custom_components.bosch.rest_heating_circuit import RestHeatingCircuit
from custom_components.bosch.rest_zone import RestZone
from custom_components.bosch.sensor.dhw_sensor import RestDhwSensor
from custom_components.bosch.sensor.zone_sensor import RestZoneSensor
from custom_components.bosch.switch import RestSystemSwitch


def _make_gateway():
    return SimpleNamespace(
        device_model="Bosch",
        device_type="CT200 (EasyControl)",
        firmware="05.04.00",
        system_cache={},
    )


def test_wrapper_object_names_match_expected_device_labels():
    """Wrapper objects should expose the intended device names."""
    gateway = MagicMock()

    zone = RestZone(client=MagicMock(), zone_id="zn1", device_id="101426422", gateway_wrapper=gateway)
    zone._name = "Lavadero"
    dhw = RestDhwCircuit(client=MagicMock(), dhw_id="dhw1", device_id="101426422", gateway_wrapper=gateway)
    hc = RestHeatingCircuit(client=MagicMock(), hc_id="hc1", device_id="101426422", gateway_wrapper=gateway)

    assert zone.device_name == "Heating Zone: Lavadero"
    assert dhw.name == "Domestic Hot Water (dhw1)"
    assert hc.name == "Heating Circuit (hc1)"


def test_system_entities_use_thermostat_device_name():
    """System entities should attach to the Thermostat child device."""
    gateway = _make_gateway()

    number = RestSystemNumber(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        gateway=gateway,
        number_type="temperature_offset",
        name_suffix="Temperature Offset",
        icon="mdi:thermometer",
        min_value=-5.0,
        max_value=5.0,
        step=0.5,
        unit="C",
    )
    switch = RestSystemSwitch(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        gateway=gateway,
        switch_type="away_mode",
        name_suffix="Away Mode",
        icon="mdi:home-export-outline",
    )

    assert number.device_name == "Thermostat"
    assert switch.device_name == "Thermostat"


def test_zone_and_dhw_entities_use_descriptive_device_names():
    """Zone and DHW entities should expose descriptive device names."""
    gateway = _make_gateway()
    zone = SimpleNamespace(
        id="zn1",
        zone_id="zn1",
        name="Lavadero",
        device_name="Heating Zone: Lavadero",
        update_initialized=False,
    )
    dhw = SimpleNamespace(
        id="dhw1",
        dhw_id="dhw1",
        name="Domestic Hot Water (dhw1)",
        update_initialized=False,
    )

    zone_sensor = RestZoneSensor(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        zone=zone,
        gateway=gateway,
        sensor_type="valve_position",
        name_suffix="Valve Position",
        icon="mdi:valve",
    )
    dhw_sensor = RestDhwSensor(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        dhw=dhw,
        gateway=gateway,
        sensor_type="actual_temp",
        name_suffix="Actual Temperature",
        icon="mdi:thermometer-water",
    )

    assert zone_sensor.device_name == "Heating Zone: Lavadero"
    assert dhw_sensor.device_name == "Domestic Hot Water (dhw1)"


def test_climate_device_info_uses_descriptive_zone_name():
    """Climate device info should use the Heating Zone label."""
    gateway = SimpleNamespace(
        device_model="Bosch",
        device_type="CT200 (EasyControl)",
        firmware="05.04.00",
    )
    zone = SimpleNamespace(
        attr_id="/zones/zn1",
        id="zn1",
        name="Lavadero",
        device_name="Heating Zone: Lavadero",
        current_temp=24.5,
        target_temperature=23.0,
        ha_modes=["off", "heat", "auto"],
        ha_mode="heat",
        state=True,
        support_presets=False,
        preset_modes=[],
        preset_mode=None,
        min_temp=5.0,
        max_temp=30.0,
        hvac_action=None,
    )

    entity = RestBoschThermostat(
        coordinator=MagicMock(),
        hass=MagicMock(),
        uuid="gateway-uuid",
        bosch_object=zone,
        gateway=gateway,
    )

    assert entity.device_info["name"] == "Heating Zone: Lavadero"
