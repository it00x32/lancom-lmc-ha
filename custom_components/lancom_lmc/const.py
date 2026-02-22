"""Constants for the LANCOM Management Cloud integration."""

DOMAIN = "lancom_lmc"
MANUFACTURER = "LANCOM Systems"

CONF_API_KEY = "api_key"
CONF_ACCOUNT_ID = "account_id"

BASE_URL = "https://cloud.lancom.de"
DEVICES_BASE = f"{BASE_URL}/cloud-service-devices"
MONITORING_BASE = f"{BASE_URL}/cloud-service-monitoring"

UPDATE_INTERVAL = 60  # seconds
