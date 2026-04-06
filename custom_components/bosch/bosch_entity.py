"""Bosch base entity."""
from .const import DOMAIN
from homeassistant.helpers.entity import DeviceInfo


class BoschEntity:
    """Bosch base entity class."""

    def __init__(self, **kwargs):
        """Initialize the entity."""
        self.hass = kwargs.get("hass")
        self._bosch_object = kwargs.get("bosch_object")
        self._gateway = kwargs.get("gateway")
        self._uuid = kwargs.get("uuid")

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Get attributes about the device."""
        return DeviceInfo(
            identifiers=self._domain_identifier,
            manufacturer=self._gateway.device_model,
            model=self._gateway.device_type,
            name=self.device_name,
            sw_version=self._gateway.firmware,
            hw_version=self._uuid,
            via_device=(DOMAIN, self._uuid),
        )
