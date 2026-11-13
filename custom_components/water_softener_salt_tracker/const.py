"""Constants for the Water Softener Salt Tracker integration."""

DOMAIN = "water_softener_salt_tracker"

CONF_WATER_METER_SENSOR = "water_meter_sensor"
CONF_SALT_CAPACITY = "salt_capacity"
CONF_CONSUMPTION_RATE = "consumption_rate"

DEFAULT_NAME = "Water Softener"
DEFAULT_SALT_CAPACITY = 8.0
DEFAULT_CONSUMPTION_RATE = 0.345

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.storage"
