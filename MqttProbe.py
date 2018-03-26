from HardwareProbe import getProbeReport as hwProbeReport
import paho.mqtt.publish as mqttPublisher
from configparser import ConfigParser
import json
import os
import sys

# Read the sensors from HardwareProbe.py and use Mqtt to publish the sensor data
def main():
    # List containing all the MQTT messages to be published.
    messagesToPublish = []


    # Config from config.ini file. This reads from start to finish.
    # The last one read will overwrite the first one read.
    config = ConfigParser(delimiters=('=',))
    config.optionxform = str
    config.read([os.path.join(sys.path[0], 'config.ini.dist'), os.path.join(sys.path[0], 'config.ini')])

    # From config get any drive lists or use the default

    # Get default broker settings from config:
    brokerHost = config['Broker'].get('host', "localhost")
    brokerTcpPort = config['Broker'].getint('port', 1883)
    clientId = config['Broker'].get('client_id', "HwProbeSensor")
    keepAlive = config['Broker'].getint('keepalive', 60)
    userName = config['Broker'].get('auth_username', None)
    passWord = config['Broker'].get('auth_password', None)

    if userName is None or passWord is None:
        # Either Username or password is not set. Both should be set before setting auth:
        print("password authentication disabled due to auth_username or auth_password is not set.")
        auth = None
    else:
        auth = {'username': userName, 'password': passWord}


    # Get HwProbeSensor settings from config.
    hwProbeTopic = config['HwProbeSensor'].get('topic', "hwprobe")
    hwProbeQos = config['HwProbeSensor'].getint('qos', 0)
    hwProbeRetain = config['HwProbeSensor'].getboolean('retain', False)
    hwProbegetDiskUsageForDrives = config['HwProbeSensor'].get('diskUsageForDrives', ".")

    # Need to convert the csv to a list so this can be used by hwProbeReport
    diskUsageForDrives = hwProbegetDiskUsageForDrives.split(",")

    # Get the Harware probe report.
    sensorDict = hwProbeReport(diskUsageForDrives)

    # for debugging:
    print(json.dumps(sensorDict))

    # Convert this to a message so we can get the next sensor
    sensorsDictmsg = {'topic': hwProbeTopic, 'payload': json.dumps(sensorDict), 'qos': hwProbeQos, 'retain': hwProbeRetain}

    # Add this message to the list
    messagesToPublish.append(sensorsDictmsg)

    # Add any other customs sensors here and append to messagesToPublish, these will be published in turn.

    # Finally publish the messages in the list:
    mqttPublisher.multiple(messagesToPublish, brokerHost, brokerTcpPort, clientId, keepAlive, None, auth)


if __name__ == '__main__':
    main()
