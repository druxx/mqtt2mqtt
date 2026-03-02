#
# TWA (Time Weighted Average) processor for MQTT messages
# reports the time-weighted average value of a specified JSON field.
#


from os import environ
import time
import json
import paho.mqtt.client as mqtt

DEBUG = environ.get('DEBUG') == '1'

twa = {}

def processMessage(data, processor_config):
    msg = None
    if 'json_field' not in processor_config:
        return None
    
    json_data = json.loads(data)
    json_field = processor_config['json_field']
    topic = processor_config['topic']
    if json_field == '' or json_field not in json_data:
        return None
    if topic not in twa:
        twa[topic] = {}

    value = json_data[json_field]
    if DEBUG:
        print(f"Extracted value for field '{json_field}': {value}")
    if 'start' not in twa[topic]:
        twa[topic]['start'] = time.time()
        twa[topic]['total_value'] = 0
        twa[topic]['value'] = value
        twa[topic]['time'] = time.time()
        return None

    elapsed_time = time.time() - twa[topic]['time']
    twa[topic]['total_value'] += twa[topic]['value'] * elapsed_time
    twa[topic]['value'] = value
    twa[topic]['time'] = time.time()
    interval = processor_config.get('interval', 150)
    if time.time() - twa[topic]['start'] >= interval:
        average_value = twa[topic]['total_value'] / (time.time() - twa[topic]['start'])
        msg = json.dumps({ json_field + '_twa': round(average_value, 2) })
        twa[topic]['start'] = time.time()
        twa[topic]['total_value'] = 0
    return msg

def getEntities():
    return [
        {
            'name': '{json_field}_twa',
            'unit': 'W', # later: get from config?
            'device_class': 'power' # later: get from config?
        }
    ]
