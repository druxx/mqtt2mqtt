# mqtt2mqtt - Receive data from mqtt, do some calculations / transformations and publish new data to mqtt

This utility allows providing data processors reacting on incoming mqtt packets. As a first example, the dutycycle processor is defined.

## duty cycle module

this module reads the messages for a specified topic and checks one of the fields in the JSON string. If the value goes below the threshold, measurement of a new cycle is started. It is  stopped with the next transition to a value below the threshold. The cycle time is reported as well as the percentage of time above threshold for this cycle. The value `dutyCycle * maxValue` is sent as well.

# Running

either
- pip install -r requirements.txt
- set environment variables specified below
- python3 mqtt2mqtt.py

or
- Use docker to launch this, docker image for linux/amd64,linux/arm64 available from ghcr.io/druxx/mqtt2mqtt


# Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` |  | Set to `1` to enable additional debug logging. |
| `HOMEASSISTANT_PREFIX` | `homeassistant` | The prefix for Home Assistant discovery. Must be the same as `discovery_prefix` in your Home Assistant configuration. |
| `MQTT_HOST` | `localhost` | The MQTT broker to connect to. |
| `MQTT_PORT` | `1883` | The port on the broker to connect to. |
| `MQTT_TOPIC_PREFIX` | `ping` | The MQTT topic prefix. With the default data will be published to `ping/<hostname>`. |
| `DUTYCYCLE_1_TOPIC` | | topic to subscribe to, example  `zigbee2mqtt/Heating_Livingroom` |
| `DUTYCYCLE_1_JSON_FIELD` | | mqtt data expected as JSON string, this is the field used to calculate the duty cycle |
| `DUTYCYCLE_1_THRESHOLD` | 10 | entity to be used to calculate the duty cycle is expected as number, this is the on-off threshold|
| `DUTYCYCLE_1_HA_DEVICE` | | if given, a message to register a new entity for this device is sent to HomeAssistant. Typical zigbee2mqtt device id: 'zigbee2mqtt_<IEEE address>', find in mqtt device registration message|

duty cycles for more than one entitity can be provided, just increase the '1' from the table above to 2,3,4,5,... 

