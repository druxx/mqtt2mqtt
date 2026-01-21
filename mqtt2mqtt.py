from os import environ
from datetime import datetime
import sys
import time
import importlib
import json
import paho.mqtt.client as mqtt

MQTT_TOPIC_PREFIX = environ.get('MQTT_TOPIC_PREFIX', 'mqtt2mqtt')
DEBUG = environ.get('DEBUG') == '1'
HOMEASSISTANT_PREFIX = environ.get('HOMEASSISTANT_PREFIX', 'homeassistant')
MQTT_CLIENT_ID = environ.get('MQTT_CLIENT_ID', 'mqtt2mqtt')
MQTT_USER = environ.get('MQTT_USER', '')
MQTT_PASSWD = environ.get('MQTT_PASSWD', '')
MQTT_HOST = environ.get('MQTT_HOST', 'localhost')
MQTT_PORT = int(environ.get('MQTT_PORT', '1883'))
MODULE_LIST = environ.get('MODULE_LIST', 'dutycycle').split(',')    

def getEnvInfo():
    list = []
    for module in MODULE_LIST:
        module_upper = module.strip().upper()
        module_number = 1
        while environ.get(f'{module_upper}_{module_number}_TOPIC'):
            topic = environ.get(f'{module_upper}_{module_number}_TOPIC')
            json_field = environ.get(f'{module_upper}_{module_number}_JSON_FIELD', '')
            threshold = environ.get(f'{module_upper}_{module_number}_THRESHOLD', 10) # value < threshold: off else on
            ha_device = environ.get(f'{module_upper}_{module_number}_HA_DEVICE', 'zigbee2mqtt_0x0c2a6ffffedc1c16')
            list.append({
                'module': module,
                'topic': topic,
                'json_field': json_field,
                'threshold': threshold,
                'ha_device': ha_device
            })
            module_number += 1
    return list



def registerHAentity(config, mqtt):
    json_field = config['json_field']
    source_split = config['topic'].split('/')
    source = source_split[len(source_split) - 1]
    entities = config['getEntities']()
    for entity in entities:
        sensor = entity['name'].format(json_field=json_field)
        state_topic = MQTT_TOPIC_PREFIX + '/' + config['module'] + '/' + source + '/' + json_field
        registration_packet = {
            'name': sensor,
            'state_topic': state_topic,
            'value_template': f'{{{{ value_json.{sensor} }}}}',
            'unit_of_measurement': entity['unit'],
            'device_class': entity['device_class'],
            'state_class': 'measurement',
            'enabled_by_default': True,
            'device': {
                'identifiers': [config['ha_device']],
            },
            'unique_id': source + '_' + sensor.replace(' ', '_').lower()
        }
        registration_topic = HOMEASSISTANT_PREFIX + '/sensor/{}/config'.format(registration_packet['unique_id'])
        mqtt.publish(registration_topic, json.dumps(registration_packet), retain=True)


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    if DEBUG:
        print()
        print(datetime.now().strftime("%H:%M:%S %Y-%m-%d"))
        print(f"Message received on topic {msg.topic}, payload: {payload}")
    for processor in processors:
        if msg.topic == processor['topic']:
            if DEBUG:
                print(f"Processing message with module {processor['module']}")
            msg = processor['process_func'](payload, processor)
            if msg is not None:
                source_split = processor['topic'].split('/')
                source = source_split[len(source_split) - 1]
                topic = MQTT_TOPIC_PREFIX + '/' + processor['module'] + '/' + source + '/' + processor['json_field']
                if DEBUG:
                    print(f"Publishing to topic {topic}: {msg}")
                try:
                    client.publish(topic, msg)
                except Exception as e:
                    print(f'MQTT Publish Failed: {e}')
                    time.sleep(5)
                    sys.exit(1)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected successfully")
    else:
        print("Connection failed, rc =", rc)


processors = getEnvInfo()
print("Configured processors:", processors)

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
print(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
client.on_connect = on_connect
client.connect(MQTT_HOST, MQTT_PORT)
client.on_message = on_message
client.publish("mqtt2mqtt/status", "online", qos=1, retain=True)

for processor in processors:
    module = importlib.import_module(processor['module'])
    func = getattr(module, "processMessage")
    processor['process_func'] = func
    client.subscribe(processor['topic'])
    print(f"Subscribed to {processor['topic']} for module {processor['module']}")
    if 'ha_device' in processor:
        processor['getEntities'] = getattr(module, "getEntities")
        registerHAentity(processor, client)

client.loop_forever()
