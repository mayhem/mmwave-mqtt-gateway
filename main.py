#!/usr/bin/env python3

import os
import sys
import math
import socket
import traceback
from time import asctime

import paho.mqtt.client as mqtt

from mmwave import MMWave

CLIENT_ID = socket.gethostname()

SENSOR_NAME = "presence-bedroom"
MQTT_HOST = "10.1.1.2"
MQTT_PORT = 1883



class MMWave_MQTT_Gateway:

    TOPIC = "zigbee2mqtt/" + config.SENSOR_NAME

    def __init__(self):
        self.mqttc = mqtt.Client(CLIENT_ID)
        self.mqttc.connect(config.MQTT_HOST, config.MQTT_PORT, 60)
        self.mqttc.loop_start()
        print("MQTT connected.")

        self.current_state = ""

        self.mmwave = MMWave(MMWave_MQTT_Gateway.on_event, self)
        self.mmwave.open()
        self.mmwave.main_loop()

    @staticmethod
    def on_event(callback_obj, event):
        callback_obj._on_event(event)

    def _on_event(self, event):
        if event is None:
            return
        with open("/home/robert/mmwave/presence.log", "a") as f:
            f.write(f"{asctime()} %s\n" % event)
        if event in ("occupied-moving", "occupied-static", "unoccupied"):
            if event != self.current_state:
                self.mqttc.publish(self.TOPIC, '{ "presence": "%s" }' % event)
                self.current_state = event


if __name__ == "__main__":
    MMWave_MQTT_Gateway()
