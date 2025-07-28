import os

# API endpoints
# BASE_API_URL = "https://api.vyomiq.com"
BASE_API_URL = "http://localhost:8001"
MACHINE_REGISTER_API_URL = f"{BASE_API_URL}/device/register/watchmen/"

# Directory structure
VYOM_ROOT_DIR = "/opt/vyomcloudbridge"
MACHINE_CONFIG_FILE = os.path.join(VYOM_ROOT_DIR, "machine_config.ini")

# Organization ID for watchmen devices
WATCHMEN_ORGANIZATION_ID = 20
