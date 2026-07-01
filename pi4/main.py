import measure
from wledClient import WLEDClient
import time
import datetime

SHUNT_OHMS = 10
LEDS = WLEDClient("10.42.0.153", leds=2)
LEDS.clear()
LEDS.display()

def f():
    n = 0
    for i in range(0, 9):
        if i == 0:
            yield 0
        else:
            n |= (1 << (i-1))
            yield n

values = [i for i in f()]
colors = []

for rV in range(len(values)):
    for gV in range(len(values)):
        for bV in range(len(values)):
            colors.append(
                values[rV] << 16 | values[gV] << 8 | values[bV]
            )
#print(values)

#colors = set(colors)

for i in colors:
    print(f" 0x{i:06x}")

print(f"{len(colors)} test colors generated.")

cpl = 0

log = open(datetime.datetime.now().strftime("%H_%M_%S.txt"), "w")
log.write("R\tG\tB\tmA\n")
try:
    for color in colors:
        LEDS.setPixel(0, color)
        LEDS.display()
        print(f"Testing 0x{color:06x}... ", end="", flush=True)
        time.sleep(0.1)
        shunt_mA = measure.getShuntVoltage(1024)/SHUNT_OHMS
        cpl += 1
        print(f"I = {shunt_mA:.03f} mA | {cpl}/{len(colors)} ({(cpl/len(colors))*100:.04f}%) done.")
        log.write(f"{(color >> 16) & 255}\t{(color >> 8) & 255}\t{color & 255}\t{shunt_mA}\n")
except KeyboardInterrupt:
    pass

log.close()
