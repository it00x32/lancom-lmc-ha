"""Constants for the LANCOM Management Cloud integration."""

DOMAIN = "lancom_lmc"
MANUFACTURER = "LANCOM Systems"

CONF_API_KEY = "api_key"
CONF_ACCOUNT_ID = "account_id"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_BETA_FIRMWARE = "beta_firmware"
CONF_NAME = "name"

DEFAULT_UPDATE_INTERVAL = 60  # Minuten
MIN_UPDATE_INTERVAL = 1
MAX_UPDATE_INTERVAL = 1440  # 24 Stunden

BASE_URL = "https://cloud.lancom.de"
DEVICES_BASE = f"{BASE_URL}/cloud-service-devices"
MONITORING_BASE = f"{BASE_URL}/cloud-service-monitoring"
USERAGENT_BASE = f"{BASE_URL}/cloud-service-useragent"
AUTH_BASE = f"{BASE_URL}/cloud-service-auth"
CONFIG_BASE = f"{BASE_URL}/cloud-service-config"
