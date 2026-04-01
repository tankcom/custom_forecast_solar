"""Energy dashboard support for Custom Forecast Solar."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_solar_forecast(
    hass: HomeAssistant,
    config_entry_id: str,
) -> dict[str, Any] | None:
    """Return solar forecast for Energy Dashboard.

    Returns flat dict mapping ISO timestamp strings to power in Watts.
    e.g. {"2026-04-01T12:00:00+02:00": 5000.0, ...}
    """
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
        _LOGGER.warning(
            "Solar forecast requested but entry not found: %s", config_entry_id
        )
        return None

    try:
        coordinator = entry.runtime_data
        forecast_data = coordinator.get_energy_forecast()

        if forecast_data:
            _LOGGER.debug(
                "Providing solar forecast with %d time slots",
                len(forecast_data),
            )
        else:
            _LOGGER.warning("No forecast data available")
            return None

        return forecast_data
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Error getting solar forecast: %s", err)
        return None
