from os import environ
import time
import json
import paho.mqtt.client as mqtt

DEBUG = environ.get('DEBUG') == '1'

previous = {}
onOffTime = {}

def processMessage(data, processor_config):
    msg = None
    if processor_config['json_field']:
        json_data = json.loads(data)
        json_field = processor_config['json_field']
        threshold = float(processor_config['threshold'])
        topic = processor_config['topic']
        if json_field != '' and json_field in json_data:
            value = json_data[json_field]
            if DEBUG:
                print(f"Extracted value for field '{json_field}': {value}")
            on = float(value) >= threshold
            if on:
                if topic not in onOffTime:
                    onOffTime[topic] = {}
                if 'onValue' not in onOffTime[topic]:
                    onOffTime[topic]['onValue'] = value
                elif value > onOffTime[topic]['onValue']:
                    onOffTime[topic]['onValue'] = value
            if topic not in previous:
                previous[topic] = on
                onOffTime[topic] = { 'onTime': time.time() if on else 0,
                                     'offTime': time.time() if not on else 0 }
            else:
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

    
