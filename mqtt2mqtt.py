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
            list.append({
                'module': module,
                'topic': topic,
                'json_field': json_field,
                'threshold': threshold
            })
            module_number += 1
    return list

def getDiscoveryHostname(hostname):
    """Return Home Assistant discovery hostname for a host.
    """
    return hostname.replace('.', '_').replace(' ', '_')

def getTopic(hostname):
    """Return MQTT topic for a host.
    """
    return f'{MQTT_TOPIC_PREFIX}/' + getDiscoveryHostname(hostname)

def getHADeviceIdentifier(hostname):
    """Return Home Assistant device identifier for a host.
    """
    return f"{MQTT_TOPIC_PREFIX.title()}_{getDiscoveryHostname(hostname)}".lower()


def getHADeviceInfo(hostname):
    """Return Home Assistant device info dictionary for a host.
    """
    return {
        'identifiers': getHADeviceIdentifier(hostname),
        'name': f"{MQTT_TOPIC_PREFIX.title()} {hostname}",
        'model': 'ping2mqtt',
        'manufacturer': 'Custom Script'
    }   


def getDefaultRegistrationPacket(hostname, sensor, entity):
    """Return default Home Assistant registration packet for a host.
    """

    registration_packet = {
        'name': sensor,
        'device': getHADeviceInfo(hostname),
        'enabled_by_default': True,
        'unique_id': getHADeviceIdentifier(hostname) + f'_{sensor}',
        'object_id': getHADeviceIdentifier(hostname) + f'_{sensor}',
        'availability_topic': 'ping/status',
        'state_topic': getTopic(hostname),
#        'json_attributes_topic': f'{MQTT_TOPIC_PREFIX}/{hostname}',
    }
    registration_packet['value_template'] = f'{{{{ value_json.{sensor} }}}}'
    if 'unit' in entity:
        registration_packet['unit_of_measurement'] = entity['unit']
    if entity['type'] == 'binary_sensor':
        registration_packet['payload_off'] = 'false'
        registration_packet['payload_on'] = 'true'
        registration_packet['device_class'] = 'connectivity'
    else:
        registration_packet['state_class'] = 'measurement'
    return registration_packet


def send_homeassistant_registration(hostname):
    """Register an MQTT device for a host.
    """
    entities = { 'alive': {'type': 'binary_sensor' }, \
        'count': { 'type': 'sensor' }, \
        'min': { 'type': 'sensor', 'unit': 'msec' }, \
        'avg': { 'type': 'sensor', 'unit': 'msec' }, \
        'max': { 'type': 'sensor', 'unit': 'msec' }, \
        'percent_dropped': { 'type': 'sensor', 'unit': '%' } }

    for key, entity in entities.items():
        registration_packet = getDefaultRegistrationPacket(hostname, key, entity)
        
        registration_topic = HOMEASSISTANT_PREFIX + '/sensor/{}/{}/config'.format(getHADeviceIdentifier(hostname), key)
#        mqtt_send(registration_topic, json.dumps(registration_packet), retain=True)



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

client.loop_forever()
