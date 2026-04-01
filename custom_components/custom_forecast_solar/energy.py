"""Energy dashboard support for Custom Forecast Solar."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_solar_forecast(
    hass: HomeAssistant,
    config_entry_id: str,
) -> dict:
    """Return solar forecast data for the Energy Dashboard."""
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
        _LOGGER.warning(
            "Solar forecast requested but entry not found: %s", config_entry_id
        )
        return {"forecasts": []}

    try:
        coordinator = entry.runtime_data
        forecast_data = coordinator.get_energy_forecast()
        
        if forecast_data.get("forecasts"):
            _LOGGER.debug(
                "Providing solar forecast with %d points",
                len(forecast_data["forecasts"]),
            )
        else:
            _LOGGER.warning("No forecast points available")
        
        return forecast_data
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Error getting solar forecast: %s", err)
        return {"forecasts": []}
