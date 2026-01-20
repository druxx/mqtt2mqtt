from os import environ
import time
import json
import paho.mqtt.client as mqtt

DEBUG = environ.get('DEBUG') == '1'

previous = {}
onOffTime = {}

def processMessage(data, processor_config):
    msg = None
    if 'json_field' not in processor_config:
        return None
    
    json_data = json.loads(data)
    json_field = processor_config['json_field']
    threshold = float(processor_config['threshold'])
    topic = processor_config['topic']
    if topic not in onOffTime:
        onOffTime[topic] = {}
    if json_field == '' or json_field not in json_data:
        return None

    value = json_data[json_field]
    if DEBUG:
        print(f"Extracted value for field '{json_field}': {value}")
    on = float(value) >= threshold
    if on:
        if 'onValue' not in onOffTime[topic]:
            onOffTime[topic]['onValue'] = value
        elif value > onOffTime[topic]['onValue']:
            onOffTime[topic]['onValue'] = value
    if topic not in previous:
        previous[topic] = on
        onOffTime[topic] = { 'onTime': time.time() if on else 0,
                             'offTime': time.time() if not on else 0 }
        return None
        
    if previous[topic] != on:
        previous[topic] = on
        if on:
            onOffTime[topic]['dToff'] = time.time() - onOffTime[topic]['offTime']
            onOffTime[topic]['onTime'] = time.time()
        else:
            onOffTime[topic]['dTon'] = time.time() - onOffTime[topic]['onTime']
            onOffTime[topic]['offTime'] = time.time()
        if not on and 'dTon' in onOffTime[topic] and 'dToff' in onOffTime[topic]:
            totalCycleTime = onOffTime[topic]['dTon'] + onOffTime[topic]['dToff']
            if totalCycleTime > 0:
                dutyCycle = (onOffTime[topic]['dTon'] / totalCycleTime) * 100
            else:
                dutyCycle = 0
            value_by_dutycycle = onOffTime[topic]['onValue'] * (dutyCycle / 100)   
            if DEBUG:
                print(f"Duty Cycle: {dutyCycle:.2f}% = {value_by_dutycycle:.2f} (ON time: {onOffTime[topic]['dTon']:.2f}s, OFF time: {onOffTime[topic]['dToff']:.2f}s)")
            msg = json.dumps({
                'duty_cycle_percent': round(dutyCycle, 2),
                json_field + '_by_dutycycle': round(value_by_dutycycle, 2)
            })
            onOffTime[topic]['onValue'] = 0
            return msg
        
    # no state change
    if not on: # still off and no state change for a while
        now = time.time()
        if 'offTime' in onOffTime[topic] and now - onOffTime[topic]['offTime'] > 300:
            onOffTime[topic]['offTime'] = now
            msg = json.dumps({ 'duty_cycle_percent': 0.0, json_field + '_by_dutycycle': 0.0})            
            return msg
        
    return None

    
