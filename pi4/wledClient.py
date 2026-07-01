import re
import socket

def is_rgb(s):
    pattern = re.compile(r'^(?:#)?[0-9A-Fa-f]{6}')
    return bool(pattern.match(s))

def gamma_correct(value, gamma=2.2):
    corrected_value = int((value / 255.0) ** gamma * 255)
    return min(max(corrected_value, 0), 255)

def apply_gamma_correction(rgb, gamma=2.2):
    return [gamma_correct(channel, gamma) for channel in rgb]

def color_to_rgb(hex_color: str | int) -> list[int]:
    if type(hex_color) == int:
        r = hex_color >> 16 & 0xff
        g = hex_color >> 8 & 0xff
        b = hex_color & 0xff
    elif type(hex_color) == str:
        if not is_rgb(hex_color):
            raise ValueError("Invalid color code.")
        if hex_color[0] == "#":
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
        else:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
    else:
        raise ValueError("Invalid color format.")

    return [r, g, b]

class WLEDClient:
    def __init__(self, address: str, port: int = 21324, leds=30, cleanup_time=255, gamma_correct=False, gamma: float=2.2):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pixels = [[0, 0, 0]] * leds
        self.__address = address
        self.__port = port
        self.cleanup_time = cleanup_time
        self.gamma_correct = gamma_correct
        self.gamma = gamma
        self.ledCount = leds

    def display(self):
        message = bytearray([2, self.cleanup_time])
        for led in self.pixels:
            if self.gamma_correct:
                led = [int(i) for i in apply_gamma_correction(led, self.gamma)]
            for color in led:
                message.append(color)
        self.__socket.sendto(message, (self.__address, self.__port))

    def setPixel(self, index: int, hex_color: str | int):
        self.pixels[index] = color_to_rgb(hex_color)

    def clear(self):
        self.pixels = [[0, 0, 0]] * self.ledCount

    def __str__(self):
        s = ""
        for y in range(20):
            for x in range(20):
                s += str(self.pixels[x*20+y]) + " "
            s += "\n"
        return s
