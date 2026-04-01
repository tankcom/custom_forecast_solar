"""Parsing helpers for source forecast sensor formats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.core import State
from homeassistant.util import dt as dt_util

from .const import FORMAT_ML, FORMAT_SOLCAST


@dataclass(slots=True)
class ForecastPoint:
    """Single forecast point in half-hour resolution."""

    period_start: datetime
    pv_estimate: float
    pv_estimate10: float
    pv_estimate90: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "pv_estimate": round(self.pv_estimate, 4),
            "pv_estimate10": round(self.pv_estimate10, 4),
            "pv_estimate90": round(self.pv_estimate90, 4),
        }


@dataclass(slots=True)
class ForecastDay:
    """Normalized forecast representation for one day."""

    forecast_date: date
    total_kwh: float
    detailed_forecast: list[ForecastPoint]
    detailed_hourly: list[dict[str, Any]]
    estimate10: float | None = None
    estimate90: float | None = None

    def as_energy_forecast(self) -> list[dict[str, Any]]:
        """Return forecast points in HA energy-compatible structure."""
        return [
            {
                "period_start": point.period_start.isoformat(),
                "pv_estimate": round(point.pv_estimate * 1000, 2),  # Convert kWh to Wh
            }
            for point in self.detailed_forecast
        ]


class ForecastParseError(ValueError):
    """Raised when a source state cannot be parsed."""


class ForecastParser:
    """Parser for supported source formats."""

    def parse(
        self,
        state: State,
        source_format: str,
        target_date: date,
    ) -> ForecastDay:
        if source_format == FORMAT_ML:
            return self._parse_ml(state, target_date)
        if source_format == FORMAT_SOLCAST:
            return self._parse_solcast(state, target_date)
        raise ForecastParseError(f"Unsupported source format: {source_format}")

    def _parse_ml(self, state: State, target_date: date) -> ForecastDay:
        attrs = state.attributes
        hours = attrs.get("hours")
        if not isinstance(hours, dict):
            raise ForecastParseError("ML format requires attributes.hours")

        tz = dt_util.DEFAULT_TIME_ZONE
        detailed_forecast: list[ForecastPoint] = []
        detailed_hourly: list[dict[str, Any]] = []

        summed_kwh = 0.0

        for hour_idx in range(24):
            key = f"{hour_idx:02d}:00"
            raw_val = hours.get(key, 0)
            try:
                hour_kwh = float(raw_val)
            except (TypeError, ValueError) as err:
                raise ForecastParseError(f"Invalid hourly value for {key}: {raw_val}") from err

            summed_kwh += hour_kwh

            start_local = datetime.combine(target_date, time(hour=hour_idx), tzinfo=tz)
            first_half = hour_kwh / 2
            second_half = hour_kwh / 2

            detailed_forecast.append(
                ForecastPoint(
                    period_start=start_local,
                    pv_estimate=first_half,
                    pv_estimate10=first_half,
                    pv_estimate90=first_half,
                )
            )
            detailed_forecast.append(
                ForecastPoint(
                    period_start=start_local + timedelta(minutes=30),
                    pv_estimate=second_half,
                    pv_estimate10=second_half,
                    pv_estimate90=second_half,
                )
            )

            detailed_hourly.append(
                {
                    "period_start": start_local.isoformat(),
                    "pv_estimate": round(hour_kwh, 4),
                    "pv_estimate10": round(hour_kwh, 4),
                    "pv_estimate90": round(hour_kwh, 4),
                }
            )

        total_kwh = _safe_float(state.state)
        if total_kwh is None:
            total_kwh = _safe_float(attrs.get("raw"))
        if total_kwh is None:
            total_kwh = summed_kwh

        return ForecastDay(
            forecast_date=target_date,
            total_kwh=round(total_kwh, 4),
            detailed_forecast=detailed_forecast,
            detailed_hourly=detailed_hourly,
        )

    def _parse_solcast(self, state: State, target_date: date) -> ForecastDay:
        attrs = state.attributes
        detailed_raw = attrs.get("detailedForecast")
        detailed_forecast: list[ForecastPoint] = []

        if isinstance(detailed_raw, list):
            for idx, item in enumerate(detailed_raw):
                if not isinstance(item, dict):
                    continue

                period_start_raw = item.get("period_start")
                period_start = dt_util.parse_datetime(str(period_start_raw))
                if period_start is None:
                    raise ForecastParseError(
                        f"Invalid period_start at detailedForecast[{idx}]"
                    )

                # Keep only points that belong to the target local day.
                if dt_util.as_local(period_start).date() != target_date:
                    continue

                pv_estimate = _safe_float(item.get("pv_estimate"))
                if pv_estimate is None:
                    raise ForecastParseError(
                        f"Missing pv_estimate at detailedForecast[{idx}]"
                    )

                pv_estimate10 = _safe_float(item.get("pv_estimate10"))
                pv_estimate90 = _safe_float(item.get("pv_estimate90"))

                detailed_forecast.append(
                    ForecastPoint(
                        period_start=period_start,
                        pv_estimate=pv_estimate,
                        pv_estimate10=pv_estimate if pv_estimate10 is None else pv_estimate10,
                        pv_estimate90=pv_estimate if pv_estimate90 is None else pv_estimate90,
                    )
                )

        if not detailed_forecast:
            total_kwh = _safe_float(attrs.get("estimate"))
            if total_kwh is None:
                total_kwh = _safe_float(state.state)
            if total_kwh is None:
                raise ForecastParseError("Solcast format requires estimate or detailedForecast")

            noon = datetime.combine(target_date, time(hour=12), tzinfo=dt_util.DEFAULT_TIME_ZONE)
            detailed_forecast = [
                ForecastPoint(
                    period_start=noon,
                    pv_estimate=total_kwh,
                    pv_estimate10=total_kwh,
                    pv_estimate90=total_kwh,
                )
            ]
        else:
            total_kwh = round(sum(point.pv_estimate for point in detailed_forecast), 4)

        hourly_bucket: dict[datetime, dict[str, float]] = {}
        for point in detailed_forecast:
            local_point = dt_util.as_local(point.period_start)
            hour_start = local_point.replace(minute=0, second=0, microsecond=0)
            bucket = hourly_bucket.setdefault(
                hour_start,
                {"pv_estimate": 0.0, "pv_estimate10": 0.0, "pv_estimate90": 0.0},
            )
            bucket["pv_estimate"] += point.pv_estimate
            bucket["pv_estimate10"] += point.pv_estimate10
            bucket["pv_estimate90"] += point.pv_estimate90

        detailed_hourly = [
            {
                "period_start": hour.isoformat(),
                "pv_estimate": round(values["pv_estimate"], 4),
                "pv_estimate10": round(values["pv_estimate10"], 4),
                "pv_estimate90": round(values["pv_estimate90"], 4),
            }
            for hour, values in sorted(hourly_bucket.items(), key=lambda item: item[0])
        ]

        estimate10 = _safe_float(attrs.get("estimate10"))
        estimate90 = _safe_float(attrs.get("estimate90"))

        return ForecastDay(
            forecast_date=target_date,
            total_kwh=round(total_kwh, 4),
            detailed_forecast=sorted(detailed_forecast, key=lambda point: point.period_start),
            detailed_hourly=detailed_hourly,
            estimate10=estimate10,
            estimate90=estimate90,
        )


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        normalized = str(value).strip().replace(",", ".")
        return float(normalized)
    except ValueError:
        return None
