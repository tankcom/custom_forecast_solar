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

    Returns {"wh_hours": OrderedDict({"ISO-timestamp": Wh_value, ...})}.
    """
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
        return None

    try:
        coordinator = entry.runtime_data
        return coordinator.get_energy_forecast()
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Error getting solar forecast")
        return None
