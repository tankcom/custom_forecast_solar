"""Sensor platform for Custom Forecast Solar."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CustomForecastCoordinator


def _day_name(day: int) -> str:
    if day == 0:
        return "Today"
    if day == 1:
        return "Tomorrow"
    return f"Day +{day}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Custom Forecast Solar sensors based on config entry."""
    coordinator: CustomForecastCoordinator = entry.runtime_data

    entities = [
        CustomForecastDaySensor(
            coordinator=coordinator,
            entry=entry,
            day=mapping.day,
        )
        for mapping in coordinator.day_mappings
    ]

    async_add_entities(entities)


class CustomForecastDaySensor(CoordinatorEntity[CustomForecastCoordinator], SensorEntity):
    """Represents one daily forecast sensor."""

    entity_description = SensorEntityDescription(
        key="forecast_day",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
    )

    def __init__(
        self,
        coordinator: CustomForecastCoordinator,
        entry: ConfigEntry,
        day: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._day = day
        self._attr_has_entity_name = True
        self._attr_name = f"Forecast {_day_name(day)}"
        self._attr_unique_id = f"{entry.entry_id}_forecast_day_{day}"

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        forecast_day = self.coordinator.get_day(self._day)
        if forecast_day is None:
            return None
        return round(forecast_day.total_kwh, 4)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return self.coordinator.get_day_attributes(self._day)

    @property
    def device_info(self) -> dict:
        """Return device metadata for all forecast sensors."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Custom Forecast Solar",
            "manufacturer": "Custom",
            "model": "Forecast Mapper",
        }
