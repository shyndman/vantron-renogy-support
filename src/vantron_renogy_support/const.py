import uuid

ENV_CHARGER_BLE_ADDRESS = "CHARGER_BLE_ADDRESS"
ENV_INVERTER_BLE_ADDRESS = "INVERTER_BLE_ADDRESS"
ENV_SHUNT_BLE_ADDRESS = "SHUNT_BLE_ADDRESS"

MQTT_HOST = "0.0.0.0"
MQTT_CLIENT = "vantron-renogy"
MQTT_WRITE_INTERVAL = 4.0
MQTT_SHUNT_STATE_TOPIC_PREFIX = MQTT_CLIENT

SHUNT_NOTIFICATION_CHARACTERISTIC = uuid.UUID("0000c411-0000-1000-8000-00805f9b34fb")
SHUNT_MQTT_STATE_TOPIC = f"{MQTT_CLIENT}/shunt/state"

CHARGER_NOTIFICATION_CHARACTERISTIC = uuid.UUID("0000fff1-0000-1000-8000-00805f9b34fb")
CHARGER_WRITE_CHARACTERISTIC = uuid.UUID("0000ffd1-0000-1000-8000-00805f9b34fb")
CHARGER_MQTT_STATE_TOPIC = f"{MQTT_CLIENT}/charger/state"
CHARGER_PUBLISH_INTERVAL = 15.0

INVERTER_NOTIFICATION_CHARACTERISTIC = uuid.UUID("0000fff1-0000-1000-8000-00805f9b34fb")
INVERTER_WRITE_CHARACTERISTIC = uuid.UUID("0000ffd1-0000-1000-8000-00805f9b34fb")
INVERTER_PUBLISH_INTERVAL = 15.0
INVERTER_MQTT_STATE_TOPIC = f"{MQTT_CLIENT}/inverter/state"

MIN_I16 = int.from_bytes([0x80, 0x00], signed=True)
