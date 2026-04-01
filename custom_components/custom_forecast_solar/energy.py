"""Energy dashboard support for Custom Forecast Solar."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_solar_forecast(
    hass: HomeAssistant,
    config_entry_id: str,
) -> dict:
    """Return solar forecast data for the Energy Dashboard."""
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
        return {"forecasts": []}

    coordinator = entry.runtime_data
    return coordinator.get_energy_forecast()
