"""Energy dashboard support for Custom Forecast Solar."""

from __future__ import annotations

from collections import OrderedDict
import importlib
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_FALLBACK_CONFIG_ENTRY_ID,
    CONF_FALLBACK_DOMAIN,
    CONF_FALLBACK_ENABLED,
    DOMAIN,
)

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
        primary_data = coordinator.get_energy_forecast()
        fallback_data = await _async_get_fallback_forecast(hass, entry, config_entry_id)
        merged = _merge_energy_forecasts(primary_data, fallback_data)
        return merged
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Error getting solar forecast")
        return None


async def _async_get_fallback_forecast(
    hass: HomeAssistant,
    entry,
    current_entry_id: str,
) -> dict[str, Any] | None:
    """Fetch optional fallback forecast from another integration."""
    options = {**entry.data, **entry.options}

    if not bool(options.get(CONF_FALLBACK_ENABLED, False)):
        return None

    fallback_domain = str(options.get(CONF_FALLBACK_DOMAIN, "")).strip()
    fallback_entry_id = str(options.get(CONF_FALLBACK_CONFIG_ENTRY_ID, "")).strip()

    if not fallback_domain or not fallback_entry_id:
        return None

    if fallback_domain == DOMAIN and fallback_entry_id == current_entry_id:
        _LOGGER.warning("Ignoring fallback to self for entry %s", current_entry_id)
        return None

    fallback_entry = hass.config_entries.async_get_entry(fallback_entry_id)
    if fallback_entry is None:
        _LOGGER.warning("Configured fallback config entry not found: %s", fallback_entry_id)
        return None
    if fallback_entry.domain != fallback_domain:
        _LOGGER.warning(
            "Configured fallback entry %s has domain %s, expected %s",
            fallback_entry_id,
            fallback_entry.domain,
            fallback_domain,
        )
        return None

    try:
        module = importlib.import_module(f"custom_components.{fallback_domain}.energy")
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Failed importing fallback energy module for %s", fallback_domain)
        return None

    fetcher = getattr(module, "async_get_solar_forecast", None)
    if fetcher is None:
        _LOGGER.warning("Fallback integration %s has no async_get_solar_forecast", fallback_domain)
        return None

    try:
        return await fetcher(hass, fallback_entry_id)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Fallback forecast call failed for %s", fallback_domain)
        return None


def _merge_energy_forecasts(
    primary_data: dict[str, Any] | None,
    fallback_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge primary forecast with fallback history for missing past slots."""
    primary_wh = _normalize_wh_hours(primary_data)
    fallback_wh = _normalize_wh_hours(fallback_data)

    if not primary_wh and not fallback_wh:
        return None
    if not primary_wh:
        return {"wh_hours": OrderedDict(sorted(fallback_wh.items()))}
    if not fallback_wh:
        return {"wh_hours": OrderedDict(sorted(primary_wh.items()))}

    merged: dict[str, float] = dict(primary_wh)
    today_start = _today_start_local()

    for ts_key, wh in fallback_wh.items():
        dt_obj = _parse_ts(ts_key)
        if dt_obj is None:
            continue

        # Only backfill historical gaps; keep current/future from primary source.
        if dt_obj < today_start and ts_key not in merged:
            merged[ts_key] = wh

    return {"wh_hours": OrderedDict(sorted(merged.items()))}


def _normalize_wh_hours(data: dict[str, Any] | None) -> dict[str, float]:
    """Convert potential wh_hours payload into a validated dict."""
    if not isinstance(data, dict):
        return {}

    raw = data.get("wh_hours")
    if not isinstance(raw, dict):
        return {}

    result: dict[str, float] = {}
    for key, value in raw.items():
        dt_obj = _parse_ts(str(key))
        if dt_obj is None:
            continue
        try:
            result[dt_obj.isoformat()] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def _parse_ts(value: str):
    """Parse timestamp string to local datetime, or None if invalid."""
    from homeassistant.util import dt as dt_util

    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    return dt_util.as_local(parsed)


def _today_start_local():
    """Return start of current local day."""
    from homeassistant.util import dt as dt_util

    return dt_util.start_of_local_day()
