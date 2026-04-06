# home-assistant-bosch-custom-component

Home Assistant custom integration for the Bosch CT200 / EasyControl thermostat.

## Scope

This repository state is focused on:

- Bosch CT200 / EasyControl
- Bosch SingleKey OAuth2 authentication
- PointT REST API

The integration is modeled-only and uses a coordinator-based, bulk-first refresh path.

## Requirements

- Home Assistant 2025.7+
- Python 3.12+
- A Bosch account that can access the CT200 through SingleKey ID / PointT

## Installation

Install as a custom component in Home Assistant, for example via HACS or by copying [`custom_components/bosch`](/Users/maxschaefer/Development/bosch-ct200/home-assistant-bosch-custom-component/custom_components/bosch) into your Home Assistant config directory.

## Configuration

1. Add the Bosch integration in Home Assistant.
2. Follow the manual browser authorization flow.
3. Paste the redirect URL or extracted authorization code into the config flow.
4. The integration will exchange the code, discover your CT200 gateway, and create the config entry.

## Debugging

Useful local tools live in:

- [`debug/refresh_pointt_token.py`](/Users/maxschaefer/Development/bosch-ct200/debug/refresh_pointt_token.py)
- [`debug/scan_all_endpoints.py`](/Users/maxschaefer/Development/bosch-ct200/debug/scan_all_endpoints.py)
- [`debug/probe_pointt_bulk.py`](/Users/maxschaefer/Development/bosch-ct200/debug/probe_pointt_bulk.py)

See [`debug/README.md`](/Users/maxschaefer/Development/bosch-ct200/debug/README.md) for usage and execution order.

## Development

Run tests from the component directory:

```bash
./venv/bin/python -m pytest -q
```
