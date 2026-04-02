# Custom Forecast Solar

Home Assistant HACS custom integration that maps custom forecast sensors to a unified solar forecast format compatible with the Energy Dashboard.

## Features

- Config Flow in the UI
- Configurable days: today up to +7 (only enabled days are used)
- Per-day selectable source format:
  - `ml` (Solar-Forecast-ML style, `attributes.hours`)
  - `solcast` (Solcast style, `attributes.detailedForecast`)
- Optional fallback integration for historical gaps (for example `solcast_solar`)
- Energy-compatible sensors (`device_class: energy`, `state_class: total`, `unit: kWh`)
- Registers as a solar forecast provider for the Energy Dashboard

## Installation (HACS)

1. Add this repository to HACS as a custom repository (type `Integration`).
2. Install the integration.
3. Restart Home Assistant.
4. Add the `Custom Forecast Solar` integration via the UI.

## Configuration

The Config Flow exposes three fields per day index `0..7`:

- `enabled` — enable this day's mapping
- `entity` — source sensor entity
- `format` — `ml` or `solcast`

Optional fallback settings:

- `fallback_enabled` — enables backfilling of missing past slots
- `fallback_domain` — integration domain (for example `solcast_solar`)
- `fallback_config_entry_id` — selected config entry from that integration

Example:

- Day 0: `sensor.remoteprognose_heute`, format `ml`
- Day 1: `sensor.remoteprognose_morgen`, format `ml`
- Day 5: `sensor.solcast_pv_forecast_forecast_day_5`, format `solcast`

## Energy Dashboard integration

After configuring the integration:

1. Open Settings → Energy
2. Under Solar, click Add solar generation or consumption
3. Select the `custom_forecast_solar` integration
4. The integration should automatically provide the configured forecasts

The integration registers itself as a solar forecast provider for all configured days.

If enabled, missing past `wh_hours` slots are backfilled from the configured fallback integration. Current and future slots from this integration are kept as primary.

Note: The Energy Dashboard will only display forecasts when at least day 0 (today) is configured.

## Supported source formats

### `ml` format

- `attributes.hours`: mapping of `"HH:00" -> kWh`
- optional daily value may appear in `state` or `attributes.raw`

### `solcast` format

- preferred: `attributes.detailedForecast` entries containing:
  - `period_start`
  - `pv_estimate`
  - optional `pv_estimate10`, `pv_estimate90`
- fallback: `attributes.estimate` or `state`

## Output

For each enabled day the integration creates an energy sensor with:

- daily value in kWh
- `detailedForecast` (ISO-formatted timestamps in half-hour intervals)
- `detailedHourly` (hourly aggregation)

These sensors are created under `sensor.custom_forecast_solar_forecast_*` in Home Assistant.

## Debugging

If the Energy Dashboard does not display the forecast:

1. Check logs: set logger for `custom_components.custom_forecast_solar`
2. Call the debug service: `custom_forecast_solar.get_forecast_debug`
3. Validate entities: ensure `sensor.custom_forecast_solar_forecast_today` exists
4. Validate sources: make sure configured source sensors exist and expose valid data

## Notes

- If a source sensor is missing or provides invalid data, the coordinator update will be marked as failed.
- Changing options will automatically reload the integration.
- The integration provides forecast data to the Energy Dashboard in Wh (watt-hours) per half-hour slot.

