# OAuth2 REST API Discovery for CT200

## Summary

The CT200 / EasyControl path in this repository uses Bosch SingleKey OAuth2 plus the PointT REST API.

## Key Findings

### Authentication

- OAuth2 with PKCE
- Redirect URI: `com.bosch.tt.dashtt.pointt://app/login`
- Working browser login flow uses the wrapped `https://singlekey-id.com/de-de/login?ReturnUrl=...` form

### API

- Base URL: `https://pointt-api.bosch-thermotechnology.com`
- Resource path format:
  `GET /pointt-api/api/v1/gateways/{deviceId}/resource/{path}`
- Bulk endpoint:
  `POST /pointt-api/api/v1/bulk`

### Device Identification

- CT200 / EasyControl device type: `rrc2`

### Endpoint Shape

- Parent resources often return `refEnum` containers with `references`
- Live values are typically returned by leaf endpoints
- Canonical rediscovery tool:
  [`../../debug/scan_all_endpoints.py`](../../debug/scan_all_endpoints.py)

### Bulk Polling

The CT200 modeled read set is suitable for bulk polling. The repository validates bulk reads for representative paths across:

- zones
- system sensors
- heating circuits
- DHW circuits

### Known Unsupported / Unauthorized Endpoint

- `/zones/zn1/humidity`

This path appears in discovery but returned `403 Forbidden` in direct testing and should not be treated as a modeled sensor.

## Related Tools

- [`../../debug/refresh_pointt_token.py`](../../debug/refresh_pointt_token.py)
- [`../../debug/scan_all_endpoints.py`](../../debug/scan_all_endpoints.py)
- [`../../debug/probe_pointt_bulk.py`](../../debug/probe_pointt_bulk.py)
