#!/usr/bin/env python

import board
import busio
import adafruit_ina219
import time

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_ina219.INA219(i2c)

def getShuntVoltage(n=256):
    a = []
    for i in range(n):
        a.append(sensor.shunt_voltage*1000)
    return sum(a)/len(a)

if __name__ == "__main__":
    while True:
        v = getShuntVoltage(1024)
        print(f"I={v/10:2.03f}mA", end="\r")
        time.sleep(0.01)

