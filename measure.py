# during this test I have modified the module to measure very low currents

import board
import busio
import adafruit_ina219
import time

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_ina219.INA219(i2c)

l = []

def get(n=256):
    a = []
    for i in range(n):
        a.append(sensor.shunt_voltage*1000)
    return sum(a)/len(a)

while True:
    v = get(4096)
    print(f"I={round(v/10, 3)}mA")
    time.sleep(0.01)

