#!/usr/bin/env python3 

from time import sleep, asctime
import sys
import serial
from struct import unpack

from crc16 import calculate_crc16

def log(*args):
    print(asctime(), *args)


class MMWave:

    def __init__(self, callback=None, callback_obj=None):
        self.ser = None
        self.callback = callback
        self.callback_obj = callback_obj

    def open(self):
        self.ser = serial.Serial(
            port='/dev/serial0',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )
        sleep(1.5)

    def close(self):
        self.ser.close()
        self.ser = None

    def init_sensor(self):

        room_type = 3
        gear_threshold = 1

        # scene_setup 
        exit = False
        while not exit:
            self.write_packet(func=2, addr1=4, addr2=0x10, data=(room_type,))
            while not exit:
                cmd, addr1, addr2, data = self.read_packet()
                if cmd == 3 and addr1 == 4 and addr2 == 0x10:
                    if data[0] == room_type:
                        print("Room type set.")
                        exit = True
                        break


        # gear
        exit = False
        while not exit:
            self.write_packet(func=2, addr1=4, addr2=0xC, data=(gear_threshold,))
            while not exit:
                cmd, addr1, addr2, data = self.read_packet()
                if cmd == 3 and addr1 == 4 and addr2 == 0xC:
                    if data[0] == gear_threshold:
                        print("Gear threshold set.")
                        exit = True
                        break


    def write_packet(self, func: int, addr1: int, addr2: int, data: list):
    
        size = len(data) + 7
        packet = bytearray((0x55, size, 0, func, addr1, addr2)) + bytearray(tuple(data))
        crc = calculate_crc16(packet)
        packet += bytearray((crc & 0xFF, (crc >> 8) & 0xFF))
        #print("send: ", end="")
        #for ch in packet:
        #    print("%02X " % int(ch), end="")
        #print()
        self.ser.write(packet)


    def read_packet(self):
        while True:
            ch = self.ser.read(1)
            if ch != b"\x55":
                print("ignore %02X " % int(ch), end="")
                continue

            break

        len_L = self.ser.read(1)
        len_H = self.ser.read(1)
        plen = int(len_L[0]) | (int(len_H[0]) << 8)
        data_len = plen - 7

        cmd = int(self.ser.read(1)[0])
        addr1 = int(self.ser.read(1)[0])
        addr2 = int(self.ser.read(1)[0])
        raw_data = self.ser.read(data_len)
        raw_crc = self.ser.read(2)
        crc_sent = raw_crc[0] | (raw_crc[1] << 8)

        data = [ int(raw_data[i]) for i in range(data_len) ]

        crc = [0x55, len_L[0], len_H[0], cmd, addr1, addr2]
        crc.extend(data)

        #log("recv: %02X %02X %02X %02X %02X %02X " % (0x55, int(len_L[0]), int(len_H[0]), cmd, addr1, addr2), end="")
        #for d in data:
        #    log("%02X " % d, end="")
        #log("%02X %02X" % (int(raw_crc[0]), int(raw_crc[1])))

        crc16 = calculate_crc16(bytearray(tuple(crc)))
        if crc16 != crc_sent:
            log("CRC mismatch!")
            log("c %04X p %04X" % (crc16, crc_sent))
            return None, None, None, None

        return cmd, addr1, addr2, data


    def packet_data_to_event_string(self, cmd, addr1, addr2, data):

        if cmd == 4:                  # Proactive report
           if addr1 == 3:             # Report sensor information 
               if addr2 == 5:         # Environmental status
                   if data[0] == 0x00 and data[1] == 0xFF and data[2] == 0xFF:
                       return "unoccupied"
                   if data[0] == 0x01 and data[1] == 0x00 and data[2] == 0xFF:
                       return "occupied-static"
                   if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x01:
                       return "occupied-moving"
               if addr2 == 6:         # Body data
                   body_data = unpack("f", bytearray(tuple(data)))  # WHY?
                   return "body-data %d" % int(body_data[0])

        return None


#              if addr2 == 7:         # Approach/away
#                  if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x01:
#                      return "no approach data"
#                  if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x02:
#                      return "approach"
#                  if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x03:
#                      return "away"
#                  if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x04:
#                      return "sustained approach"
#                  if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x05:
#                      return "sustained away"
#          if addr1 == 5:             # Report other information
#              if addr2 == 1:         # Heartbeat package
#                  if data[0] == 0x00 and data[1] == 0xFF and data[2] == 0xFF:
#                      return "HB unoccupied"
#                  if data[0] == 0x01 and data[1] == 0x00 and data[2] == 0xFF:
#                      return "HB occupied & static"
#                  if data[0] == 0x01 and data[1] == 0x01 and data[2] == 0x00:
#                      return "HB occupied & moving"


    def main_loop(self):
        self.init_sensor()
        while True:
            cmd, addr1, addr2, data = self.read_packet()
            #log("cmd %d, addr1 %d addr2 %s" % (cmd, addr1, addr2))
            update_str = self.packet_data_to_event_string(cmd, addr1, addr2, data)
            if self.callback is not None:
                self.callback(self.callback_obj, update_str)
            else:
                log(update_str)


if __name__ == "__main__":
    mm = MMWave()
    mm.open()
    try:
        mm.main_loop();
    except KeyboardInterrupt:
        mm.close()
        sys.exit(0)
