"""Constants for the Custom Forecast Solar integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "custom_forecast_solar"
PLATFORMS: Final = ["sensor"]

CONF_DAY_MAPPINGS: Final = "day_mappings"
CONF_DAY: Final = "day"
CONF_ENTITY_ID: Final = "entity_id"
CONF_SOURCE_FORMAT: Final = "source_format"

FORMAT_ML: Final = "ml"
FORMAT_SOLCAST: Final = "solcast"
SUPPORTED_FORMATS: Final = (FORMAT_ML, FORMAT_SOLCAST)

MIN_DAY_OFFSET: Final = 0
MAX_DAY_OFFSET: Final = 7

SCAN_INTERVAL: Final = timedelta(minutes=15)
ENERGY_HISTORY_DAYS: Final = 14

ATTR_DETAILED_FORECAST: Final = "detailedForecast"
ATTR_DETAILED_HOURLY: Final = "detailedHourly"
ATTR_DATA_CORRECT: Final = "dataCorrect"
ATTR_FORECAST_SOURCE_ENTITY: Final = "forecast_source_entity"
ATTR_FORECAST_SOURCE_FORMAT: Final = "forecast_source_format"
