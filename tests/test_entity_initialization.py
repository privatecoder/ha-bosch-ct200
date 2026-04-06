"""Regression tests for CoordinatorEntity-based Bosch entities."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.bosch.sensor.dhw_sensor import RestDhwSensor
from custom_components.bosch.sensor.heating_circuit_sensor import (
    RestHeatingCircuitSensor,
)
from custom_components.bosch.sensor.system_sensor import RestSystemSensor
from custom_components.bosch.sensor.zone_sensor import RestZoneSensor


@pytest.fixture
def coordinator():
    """Return a minimal coordinator mock."""
    return MagicMock()


@pytest.fixture
def gateway():
    """Return a minimal gateway wrapper mock."""
    return SimpleNamespace(
        device_model="Bosch",
        device_type="CT200 (EasyControl)",
        firmware="05.04.00",
        get_cached_resource=lambda path: None,
    )


@pytest.mark.parametrize(
    ("entity_cls", "bosch_object", "kwargs"),
    [
        (
            RestZoneSensor,
            SimpleNamespace(id="zn1", zone_id="zn1", name="Zone zn1", update_initialized=False),
            {
                "sensor_type": "valve_position",
                "name_suffix": "Valve Position",
                "icon": "mdi:valve",
            },
        ),
        (
            RestHeatingCircuitSensor,
            SimpleNamespace(
                id="hc1", hc_id="hc1", name="Heating Circuit hc1", update_initialized=False
            ),
            {
                "sensor_type": "supply_temp_setpoint",
                "name_suffix": "Supply Temp Setpoint",
                "icon": "mdi:thermometer",
            },
        ),
        (
            RestDhwSensor,
            SimpleNamespace(id="dhw1", dhw_id="dhw1", name="DHW dhw1", update_initialized=False),
            {
                "sensor_type": "actual_temp",
                "name_suffix": "Actual Temperature",
                "icon": "mdi:thermometer-water",
            },
        ),
        (
            RestSystemSensor,
            None,
            {
                "sensor_type": "outdoor_temperature",
                "name_suffix": "Outdoor Temperature",
                "icon": "mdi:thermometer",
            },
        ),
    ],
)
def test_coordinator_entities_initialize_without_passing_hass_to_coordinator(
    coordinator, gateway, entity_cls, bosch_object, kwargs
):
    """Coordinator-based entities must initialize without TypeError."""
    init_kwargs = {
        "coordinator": coordinator,
        "hass": MagicMock(),
        "uuid": "gateway-uuid",
        "gateway": gateway,
        **kwargs,
    }
    if entity_cls is RestZoneSensor:
        init_kwargs["zone"] = bosch_object
    elif entity_cls is RestHeatingCircuitSensor:
        init_kwargs["hc"] = bosch_object
    elif entity_cls is RestDhwSensor:
        init_kwargs["dhw"] = bosch_object

    entity = entity_cls(**init_kwargs)

    assert entity is not None
    assert entity.unique_id
