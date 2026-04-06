"""Support for Bosch REST sensors."""
from ..const import COORDINATOR, DOMAIN, GATEWAY, SENSOR, UUID
from .dhw_sensor import RestDhwSensor
from .heating_circuit_sensor import RestHeatingCircuitSensor
from .system_sensor import RestSystemSensor
from .zone_sensor import RestZoneSensor

ZONE_SENSOR_TYPES = [
    ("valve_position", "Valve Position", "mdi:valve"),
    ("next_setpoint_temp", "Next Setpoint", "mdi:thermometer-chevron-up"),
    ("time_to_next_setpoint", "Time to Next Setpoint", "mdi:clock-outline"),
    ("optimum_start_active", "Optimum Start", "mdi:rocket-launch"),
    ("window_detection_enabled", "Window Detection", "mdi:window-open-variant"),
    ("window_open", "Window Status", "mdi:window-closed"),
    ("optimum_start_heatup_rate", "Heatup Rate", "mdi:speedometer"),
]

SYSTEM_SENSOR_TYPES = [
    ("indoor_humidity", "Indoor Humidity", "mdi:water-percent"),
    ("outdoor_temperature", "Outdoor Temperature", "mdi:thermometer"),
    ("indoor_air_temperature", "Indoor Air Temperature", "mdi:home-thermometer"),
    ("indoor_chip_temperature", "Chip Temperature", "mdi:chip"),
    ("indoor_pcb_temperature", "PCB Temperature", "mdi:expansion-card"),
]

HEATING_CIRCUIT_SENSOR_TYPES = [
    ("supply_temp_setpoint", "Supply Temp Setpoint", "mdi:thermometer-lines"),
    ("min_outdoor_temp", "Min Outdoor Temp", "mdi:thermometer-low"),
    ("night_threshold", "Night Threshold", "mdi:weather-night"),
    ("suwi_threshold", "Summer/Winter Threshold", "mdi:sun-snowflake"),
    ("operating_season", "Operating Season", "mdi:calendar-range"),
    ("boost_mode", "Boost Mode", "mdi:rocket-launch"),
    ("night_switch_mode", "Night Switch Mode", "mdi:moon-waning-crescent"),
    ("suwi_switch_mode", "Summer/Winter Switch Mode", "mdi:autorenew"),
    ("boost_remaining_time", "Boost Remaining Time", "mdi:timer-sand"),
]

DHW_SENSOR_TYPES = [
    ("actual_temp", "Actual Temperature", "mdi:thermometer"),
    ("hot_water_system", "Hot Water System", "mdi:water-boiler"),
    ("state", "State", "mdi:water"),
    ("operation_mode", "Operation Mode", "mdi:water-sync"),
    ("extra_dhw", "Extra DHW", "mdi:water-plus"),
    (
        "thermal_disinfect_last_result",
        "Thermal Disinfect Last Result",
        "mdi:check-circle",
    ),
    (
        "thermal_disinfect_state",
        "Thermal Disinfect State",
        "mdi:shield-thermometer-outline",
    ),
    (
        "thermal_disinfect_weekday",
        "Thermal Disinfect Weekday",
        "mdi:calendar-week",
    ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Bosch REST sensors from a config entry."""
    uuid = config_entry.data[UUID]
    data = hass.data[DOMAIN][uuid]
    coordinator = data[COORDINATOR]
    gateway = data[GATEWAY]
    sensors = []

    for zone in gateway.zones:
        for sensor_type, name_suffix, icon in ZONE_SENSOR_TYPES:
            sensors.append(
                RestZoneSensor(
                    coordinator,
                    hass=hass,
                    uuid=uuid,
                    zone=zone,
                    gateway=gateway,
                    sensor_type=sensor_type,
                    name_suffix=name_suffix,
                    icon=icon,
                    is_enabled=True,
                )
            )

    for sensor_type, name_suffix, icon in SYSTEM_SENSOR_TYPES:
        sensors.append(
            RestSystemSensor(
                coordinator,
                hass=hass,
                uuid=uuid,
                gateway=gateway,
                sensor_type=sensor_type,
                name_suffix=name_suffix,
                icon=icon,
                is_enabled=True,
            )
        )

    for heating_circuit in gateway.rest_heating_circuits:
        for sensor_type, name_suffix, icon in HEATING_CIRCUIT_SENSOR_TYPES:
            sensors.append(
                RestHeatingCircuitSensor(
                    coordinator,
                    hass=hass,
                    uuid=uuid,
                    hc=heating_circuit,
                    gateway=gateway,
                    sensor_type=sensor_type,
                    name_suffix=name_suffix,
                    icon=icon,
                    is_enabled=True,
                )
            )

    for dhw in gateway.dhw_circuits:
        for sensor_type, name_suffix, icon in DHW_SENSOR_TYPES:
            sensors.append(
                RestDhwSensor(
                    coordinator,
                    hass=hass,
                    uuid=uuid,
                    dhw=dhw,
                    gateway=gateway,
                    sensor_type=sensor_type,
                    name_suffix=name_suffix,
                    icon=icon,
                    is_enabled=True,
                )
            )

    data[SENSOR] = sensors
    async_add_entities(sensors)
    return True
