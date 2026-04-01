"""Data update coordinator for Custom Forecast Solar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DATA_CORRECT,
    ATTR_DETAILED_FORECAST,
    ATTR_DETAILED_HOURLY,
    ATTR_FORECAST_SOURCE_ENTITY,
    ATTR_FORECAST_SOURCE_FORMAT,
    CONF_DAY,
    CONF_DAY_MAPPINGS,
    CONF_ENTITY_ID,
    CONF_SOURCE_FORMAT,
    SCAN_INTERVAL,
)
from .parser import ForecastDay, ForecastParseError, ForecastParser


@dataclass(slots=True)
class DayMapping:
    """Single configured day mapping."""

    day: int
    entity_id: str
    source_format: str


@dataclass(slots=True)
class CoordinatorData:
    """Coordinator payload."""

    by_day: dict[int, ForecastDay]
    source_meta: dict[int, DayMapping]


class CustomForecastCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Coordinator that normalizes all configured forecast sources."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.config_entry = entry
        self._parser = ForecastParser()

        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="custom_forecast_solar",
            update_interval=SCAN_INTERVAL,
        )

    @property
    def day_mappings(self) -> list[DayMapping]:
        """Return configured day mappings from options or data."""
        raw = self.config_entry.options.get(
            CONF_DAY_MAPPINGS,
            self.config_entry.data.get(CONF_DAY_MAPPINGS, []),
        )
        mappings: list[DayMapping] = []

        for item in raw:
            mappings.append(
                DayMapping(
                    day=int(item[CONF_DAY]),
                    entity_id=str(item[CONF_ENTITY_ID]),
                    source_format=str(item[CONF_SOURCE_FORMAT]),
                )
            )

        return sorted(mappings, key=lambda item: item.day)

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from configured source sensors."""
        by_day: dict[int, ForecastDay] = {}
        source_meta: dict[int, DayMapping] = {}

        now_local = dt_util.now()

        for mapping in self.day_mappings:
            source_state = self.hass.states.get(mapping.entity_id)
            if source_state is None:
                raise UpdateFailed(f"Configured sensor not found: {mapping.entity_id}")

            target_date = (now_local + timedelta(days=mapping.day)).date()

            try:
                forecast_day = self._parser.parse(
                    state=source_state,
                    source_format=mapping.source_format,
                    target_date=target_date,
                )
            except ForecastParseError as err:
                raise UpdateFailed(
                    f"Failed parsing {mapping.entity_id} ({mapping.source_format}): {err}"
                ) from err

            by_day[mapping.day] = forecast_day
            source_meta[mapping.day] = mapping

        return CoordinatorData(by_day=by_day, source_meta=source_meta)

    def get_day(self, day: int) -> ForecastDay | None:
        """Return forecast day data for the requested offset."""
        if self.data is None:
            return None
        return self.data.by_day.get(day)

    def get_day_attributes(self, day: int) -> dict[str, Any]:
        """Return entity attributes for one day sensor."""
        if self.data is None:
            return {ATTR_DATA_CORRECT: False}

        forecast = self.data.by_day.get(day)
        mapping = self.data.source_meta.get(day)

        if forecast is None or mapping is None:
            return {ATTR_DATA_CORRECT: False}

        attrs: dict[str, Any] = {
            ATTR_DATA_CORRECT: True,
            ATTR_DETAILED_FORECAST: [point.as_dict() for point in forecast.detailed_forecast],
            ATTR_DETAILED_HOURLY: forecast.detailed_hourly,
            ATTR_FORECAST_SOURCE_ENTITY: mapping.entity_id,
            ATTR_FORECAST_SOURCE_FORMAT: mapping.source_format,
        }

        if forecast.estimate10 is not None:
            attrs["estimate10"] = round(forecast.estimate10, 4)
        if forecast.estimate90 is not None:
            attrs["estimate90"] = round(forecast.estimate90, 4)

        return attrs

    def get_energy_forecast(self) -> dict[str, Any]:
        """Return energy dashboard forecast payload."""
        if self.data is None:
            return {"forecasts": []}

        points: list[dict[str, Any]] = []
        for day in sorted(self.data.by_day):
            points.extend(self.data.by_day[day].as_energy_forecast())

        points.sort(key=lambda item: item["period_start"])
        return {"forecasts": points}
