"""The Custom Forecast Solar integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import CustomForecastCoordinator

_LOGGER = logging.getLogger(__name__)

# Import energy module functions to ensure they're discoverable
from . import energy as energy_module  # noqa: F401
from .services import async_setup_services


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Custom Forecast Solar from a config entry."""
    _LOGGER.debug("Setting up Custom Forecast Solar for %s", entry.entry_id)
    
    coordinator = CustomForecastCoordinator(hass=hass, entry=entry)
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    entry.runtime_data = coordinator
    
    # Set up services on first integration
    if not hass.data.get(DOMAIN):
        hass.data[DOMAIN] = {}
        await async_setup_services(hass)
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
