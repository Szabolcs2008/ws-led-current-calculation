class Screen:
    def __init__(self, target: str):
        self.width = 0
        self.height = 0
        self.bytes_per_pixel = 0

    def display(self):
        ...

    def set(self, __i: int, __color: int):
        ...

    def fill(self, __color):
        ...

    def clear(self):
        ...

    def get_pixel(self, __index) -> int:
        ...

class GenericDevice:
    def __init__(self, target: str):
        pass

    def packet(self, data: bytearray):  # !! Might change this name later
        pass
