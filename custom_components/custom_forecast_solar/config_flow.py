"""Config flow for Custom Forecast Solar."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_DAY,
    CONF_DAY_MAPPINGS,
    CONF_ENTITY_ID,
    CONF_SOURCE_FORMAT,
    DOMAIN,
    FORMAT_ML,
    FORMAT_SOLCAST,
    MAX_DAY_OFFSET,
    MIN_DAY_OFFSET,
)


def _day_key(prefix: str, day: int, field: str) -> str:
    return f"{prefix}_{day}_{field}"


def _build_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build the form schema for all configurable days."""
    defaults = defaults or {}
    options: dict[vol.Marker, Any] = {}

    for day in range(MIN_DAY_OFFSET, MAX_DAY_OFFSET + 1):
        enabled_key = _day_key("day", day, "enabled")
        entity_key = _day_key("day", day, "entity")
        format_key = _day_key("day", day, "format")

        options[vol.Optional(enabled_key, default=bool(defaults.get(enabled_key, False)))] = bool
        options[
            vol.Optional(
                entity_key,
                default=defaults.get(entity_key, ""),
            )
        ] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        )
        options[
            vol.Optional(
                format_key,
                default=defaults.get(format_key, FORMAT_ML),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[FORMAT_ML, FORMAT_SOLCAST],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="source_format",
            )
        )

    return vol.Schema(options)


def _extract_day_mappings(
    hass,
    user_input: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Validate user input and return normalized day mappings and errors."""
    day_mappings: list[dict[str, Any]] = []
    errors: dict[str, str] = {}

    for day in range(MIN_DAY_OFFSET, MAX_DAY_OFFSET + 1):
        enabled_key = _day_key("day", day, "enabled")
        entity_key = _day_key("day", day, "entity")
        format_key = _day_key("day", day, "format")

        enabled = bool(user_input.get(enabled_key, False))
        entity_id = (user_input.get(entity_key) or "").strip()
        source_format = (user_input.get(format_key) or FORMAT_ML).strip()

        if not enabled:
            continue

        if not entity_id:
            errors[entity_key] = "required"
            continue

        if hass.states.get(entity_id) is None:
            errors[entity_key] = "entity_not_found"
            continue

        if source_format not in (FORMAT_ML, FORMAT_SOLCAST):
            errors[format_key] = "invalid_format"
            continue

        day_mappings.append(
            {
                CONF_DAY: day,
                CONF_ENTITY_ID: entity_id,
                CONF_SOURCE_FORMAT: source_format,
            }
        )

    if not errors and not day_mappings:
        errors["base"] = "no_days_configured"

    return day_mappings, errors


def _inflate_defaults(day_mappings: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert persisted day mappings to form defaults."""
    defaults: dict[str, Any] = {}
    for mapping in day_mappings:
        day = int(mapping[CONF_DAY])
        defaults[_day_key("day", day, "enabled")] = True
        defaults[_day_key("day", day, "entity")] = mapping[CONF_ENTITY_ID]
        defaults[_day_key("day", day, "format")] = mapping[CONF_SOURCE_FORMAT]
    return defaults


class CustomForecastSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Custom Forecast Solar."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            day_mappings, errors = _extract_day_mappings(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title="Custom Forecast Solar",
                    data={CONF_DAY_MAPPINGS: day_mappings},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow for this handler."""
        return CustomForecastSolarOptionsFlow(config_entry)


class CustomForecastSolarOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Custom Forecast Solar."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            day_mappings, errors = _extract_day_mappings(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={CONF_DAY_MAPPINGS: day_mappings},
                )

        existing = self._config_entry.options.get(
            CONF_DAY_MAPPINGS,
            self._config_entry.data.get(CONF_DAY_MAPPINGS, []),
        )
        defaults = _inflate_defaults(existing)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
            errors=errors,
        )
