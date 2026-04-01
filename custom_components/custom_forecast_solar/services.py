"""Services for Custom Forecast Solar."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import CustomForecastCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_FORECAST_DEBUG = "get_forecast_debug"


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Custom Forecast Solar."""

    async def handle_get_forecast_debug(call: ServiceCall) -> None:
        """Debug service to dump forecast data."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.runtime_data is None:
                continue
            coordinator: CustomForecastCoordinator = entry.runtime_data
            forecast_data = coordinator.get_energy_forecast()
            _LOGGER.info(
                "DEBUG Forecast for %s: %d points",
                entry.entry_id,
                len(forecast_data.get("forecasts", [])),
            )
            for idx, point in enumerate(forecast_data.get("forecasts", [])[:5]):
                _LOGGER.info("  Point %d: %s", idx, point)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_FORECAST_DEBUG,
        handle_get_forecast_debug,
        description="Get forecast debug data",
    )
