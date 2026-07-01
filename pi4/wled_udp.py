import re
import socket
import urllib.parse
import hardware

def find_difference(buf1: bytearray, buf2: bytearray) -> tuple[int, int] | None:
    """
    Finds the difference between two byte arrays. Returns the start and end index of the difference.

    :param buf1: Byte array A
    :param buf2: Byte array B
    :return: (Start index of difference, End index of difference) or None if there is no difference.
    """

    if len(buf1) != len(buf2):
        raise ValueError("The arrays must be the same length.")

    if len(buf1) % 3 != 0:
        raise ValueError("Invalid array data.")

    first = -1
    last = -1

    for i in range(0, len(buf1), 3):
        if buf1[i:i+3] != buf2[i:i+3]:
            if first == -1:
                first = i
            last = i

    if first != -1 and last != -1:
        return first, last
    else:
        return None

def is_rgb(s):
    pattern = re.compile(r'^(?:#)?[0-9A-Fa-f]{6}')
    return bool(pattern.match(s))

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

class Font:
    def __init__(self, font_dict):
        self.__charmap = font_dict["charmap"]
        self.__height = font_dict["font-height"]

    @property
    def charmap(self) -> dict:
        return self.__charmap

    @property
    def height(self) -> int:
        return self.__height

    def bitmap(self, c) -> tuple[list[int], int]:
        return self.__charmap[c]["bitmap"], self.__charmap[c]["width"]

class UDPWledScreen(hardware.Screen):
    def __init__(self, target: str, cleanup=255, gamma_correct=False):
        super().__init__(target)

        self.bytes_per_pixel = 3

        parsed = urllib.parse.urlparse(target)
        params = urllib.parse.parse_qs(parsed.query)

        current_limit = params.get("clim", [])  # Get current limit as milliamperes
        current_per_led = params.get("cled", [])
        current_limit_type = params.get("ctyp", [])

        self._current_limit_ma = 0
        self._current_per_led = 0
        self._current_limit_mode = None

        if current_limit:
            self._current_limit_ma = int(current_limit[0])

        if current_per_led:
            self._current_per_led = int(current_per_led[0])

        if current_limit_type:
            self._current_limit_type = str(current_limit_type[0]).lower()

            if self._current_limit_type not in ["normal", "cc"]:
                raise ValueError("Invalid current limit type. Valid values are: NORMAL, CC")

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.screensize = [int(_) for _ in params["screen"][0].split("x") if _]

        self.width = self.screensize[0]
        self.height = self.screensize[1]
        self.__leds = self.width*self.height
        self.pixel_bytearray_PRIMARY = bytearray(self.__leds * 3)  # Last shown frame
        self.pixel_bytearray_SECONDARY = bytearray(self.__leds * 3)  # Write updates into this


        self.__address = parsed.hostname
        self.__port = parsed.port
        self.__debug__disable__limits = False
        self.cleanup = cleanup
        self.gamma_correct = gamma_correct

        self.boot = True

        self.__current_estimate = bytearray(self.__leds)  # Current per LED should never realistically be able to exceed 255 mA

    def display(self):
        diff = find_difference(self.pixel_bytearray_PRIMARY, self.pixel_bytearray_SECONDARY)

        if self.boot:
            self.boot = False
            diff = (0, len(self.pixel_bytearray_SECONDARY)-1)

        if not diff:
            self.__socket.sendto(bytes([self.pixel_bytearray_PRIMARY[0]]), (self.__address, self.__port))
            return

        data = self.pixel_bytearray_SECONDARY[diff[0]:diff[1] + 3+1] # +1 needed because of python

        self.pixel_bytearray_PRIMARY = self.pixel_bytearray_SECONDARY.copy()

        if len(data) < 481 or self.__debug__disable__limits:
            message = bytearray([4, self.cleanup])
            message += (diff[0]//3).to_bytes(2, "big")
            message += data
            self.__socket.sendto(message, (self.__address, self.__port))
        else:
            # else we have to use DNGRB
            for packet in self.__split_packets(data, start_pos=diff[0]//3):
                self.__socket.sendto(packet, (self.__address, self.__port))

    def __split_packets(self, led_data: bytes, start_pos: int = 0):
        """
        :param led_data: bytearray of raw LED data
        :return: List of valid DNRGB packets for WLED
        """
        packets: list[bytearray] = []
        for i in range(0, len(led_data)//3, 480):
            l_packet = bytearray(led_data[i*3:(i + 480)*3])
            packet = bytearray([4, self.cleanup])
            packet += (i+start_pos).to_bytes(2, "big")
            packet += l_packet
            packets.append(packet)
        return packets


    def set(self, index: int, hex_color: str | int):
        rgb = color_to_rgb(hex_color)

        self.pixel_bytearray_SECONDARY[index*3 + 0] = rgb[0]
        self.pixel_bytearray_SECONDARY[index*3 + 1] = rgb[1]
        self.pixel_bytearray_SECONDARY[index*3 + 2] = rgb[2]

    def fill(self, hex_color):
        for i in range(self.__leds):
            self.set(i, hex_color)

    def clear(self):
        self.pixel_bytearray_SECONDARY = bytearray(self.__leds * 3)

    def get_pixel(self, __index) -> int:
        return int.from_bytes(self.pixel_bytearray_SECONDARY[__index*3 : (__index+1)*3])
