# Custom Forecast Solar

Home Assistant HACS Custom Integration, die benutzerdefinierte Prognose-Sensoren auf ein einheitliches Solar-Forecast-Format fuer das Energy Dashboard abbildet.

## Features

- Config Flow in der UI
- Variable Tage: heute bis +7 (nur aktivierte Tage)
- Pro Tag frei waehbares Quellformat:
  - `ml` (Solar-Forecast-ML Stil, `attributes.hours`)
  - `solcast` (Solcast Stil, `attributes.detailedForecast`)
- Energy-kompatible Sensorsignale (`device_class: energy`, `state_class: total`, `unit: kWh`)
- Energy Hook via `async_get_solar_forecast`

## Installation (HACS)

1. Dieses Repository in HACS als Custom Repository (Typ `Integration`) hinzufuegen.
2. Integration installieren.
3. Home Assistant neu starten.
4. Integration `Custom Forecast Solar` ueber UI hinzufuegen.

## Konfiguration

Im Config Flow gibt es pro Tag `0..7` drei Felder:

- `enabled`
- `entity` (Quell-Sensor)
- `format` (`ml` oder `solcast`)

Beispiel:

- Tag 0: `sensor.remoteprognose_heute`, Format `ml`
- Tag 1: `sensor.remoteprognose_morgen`, Format `ml`
- Tag 5: `sensor.solcast_pv_forecast_forecast_day_5`, Format `solcast`

## Erwartete Quellen

### Format `ml`

- `attributes.hours`: Map `"HH:00" -> kWh`
- optionaler Tageswert in `state` oder `attributes.raw`

### Format `solcast`

- bevorzugt `attributes.detailedForecast` mit Eintraegen:
  - `period_start`
  - `pv_estimate`
  - optional `pv_estimate10`, `pv_estimate90`
- fallback: `attributes.estimate` oder `state`

## Output

Die Integration erzeugt je aktiviertem Tag einen Energy-Sensor mit:

- Tageswert in kWh
- `detailedForecast`
- `detailedHourly`

Zusatzlich stellt `energy.py` ein Forecast-Dictionary fuer das Energy Dashboard bereit.

## Hinweise

- Wenn ein Quellsensor fehlt oder ungueltige Daten liefert, wird der Update-Lauf als fehlgeschlagen markiert.
- Nach Aenderungen in den Optionen wird die Integration automatisch neu geladen.
