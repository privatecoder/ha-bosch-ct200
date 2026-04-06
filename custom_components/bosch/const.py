"""Constants for the bosch component."""
from datetime import timedelta

DOMAIN = "bosch"
ACCESS_TOKEN = "access_token"
UUID = "uuid"

GATEWAY = "gateway"
CLIMATE = "climate"
SENSOR = "sensor"
NUMBER = "number"
SELECT = "select"
SWITCH = "switch"
VALUE = "value"
ENTRY_ID = "entry_id"

DEFAULT_MIN_TEMP = 0
DEFAULT_MAX_TEMP = 100

SERVICE_PUT_STRING = "send_custom_put_string"
SERVICE_PUT_FLOAT = "send_custom_put_float"
SERVICE_GET = "send_custom_get"
SERVICE_UPDATE = "update_thermostat"

SCAN_INTERVAL = timedelta(seconds=60)

DEVICE_ID = "device_id"
REFRESH_TOKEN = "refresh_token"
COORDINATOR = "coordinator"

# OAuth2 endpoints
OAUTH_CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
OAUTH_AUTH_URL = "https://singlekey-id.com/auth/connect/authorize"
OAUTH_TOKEN_URL = "https://singlekey-id.com/auth/connect/token"
OAUTH_REDIRECT_URI = "com.bosch.tt.dashtt.pointt://app/login"
POINTT_API_BASE_URL = "https://pointt-api.bosch-thermotechnology.com"
OAUTH_LOGIN_URL = "https://singlekey-id.com/de-de/login"
OAUTH_LOGIN_FLOW_ID = "R-mPKKXSaQ"

# OAuth2 scopes
OAUTH_SCOPES = (
    "openid email profile offline_access "
    "pointt.gateway.claiming pointt.gateway.removal "
    "pointt.gateway.list pointt.gateway.users "
    "pointt.gateway.resource.dashapp "
    "pointt.castt.flow.token-exchange "
    "bacon hcc.tariff.read"
)
