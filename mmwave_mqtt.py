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

class MMWave_MQTT_Gateway:

    TOPIC = "zigbee2mqtt/bedroom-presence-sensor"

    def __init__(self):
        self.mqttc = mqtt.Client(CLIENT_ID)
        self.mqttc.connect("10.1.1.2", 1883, 60)
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
        print(f"{asctime()} %s" % event)
        if event in ("occupied-moving", "occupied-static", "unoccupied"):
            if event != self.current_state:
                self.mqttc.publish(self.TOPIC, '{ "presence": "%s" }' % event)
                self.current_state = event


if __name__ == "__main__":
    MMWave_MQTT_Gateway()
