# MqttProber
Simple Mqtt script that publishes multiple sensor values from the os it's running on and immediately transmits
these values as json to the broker.

To run create your own config.ini and use
```python
python MqttProbe.py
```

## Requirements
**Python 3**
1. paho-mqtt
2. psutil
3. simplejson

**Linux**
1. sysstat
2. update-notifier-common (optional)