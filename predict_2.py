from colorama import Fore
import colorama

colorama.init(autoreset=True)

MA_PER_LED = 10
MA_IDLE = 0.5

PHASE_SHIFT_R = 0
PHASE_SHIFT_G = 63
PHASE_SHIFT_B = 127


with open("1led.txt") as f:
    data = f.readlines()

    table: list[dict[str, float | int]] = []

    # Everything but using pandas
    h: list = data[0].strip().split("\t")
    for row in data[1:]:
        row = row.strip().split("\t")
        r = {}
        for i in range(len(h)):
            r[h[i]] = float(row[i])
        table.append(r)

def calculate_current(rgb: tuple[int, int, int]):
    if rgb == (0, 0, 0):
        return MA_IDLE
    
    r, g, b = rgb

    # val = min(sum(rgb), 255)
    val = r + g + b

    if g and r:
        g_start = 63
        g_end = (63 + g) % 256
        r_start = 0
        r_end = r

        g_i = min(g_end, r_end) - g_start if r > 64 else 0
        if g > 192:
            g_i = g_i + r

        val -= g_i
        
        
    
    return MA_PER_LED * (val / 255) + MA_IDLE

def verify(r_range, g_range, b_range):
    _fail = 0
    _pass = 0

    for row in table:
        rgb = int(row["R"]), int(row["G"]), int(row["B"])
        if not ((rgb[0] in r_range) and (rgb[1] in g_range) and (rgb[2] in b_range)): 
            # print(f"{Fore.YELLOW}SKIP: rgb=({rgb[0]:03}, {rgb[1]:03}, {rgb[2]:03})")
            continue
        expected_mA = row["mA"]
        calculated_mA = calculate_current(rgb)

        err = (calculated_mA / expected_mA) - 1
        if err < -0.05 or err > 0.25:
            print(f"{Fore.RED}FAIL: rgb=({rgb[0]:03}, {rgb[1]:03}, {rgb[2]:03}), expected={expected_mA:.04f}mA, calculated={calculated_mA:.04f}mA, error={err*100:.02f}%")
            _fail += 1
        else:
            print(f"PASS: rgb=({rgb[0]:03}, {rgb[1]:03}, {rgb[2]:03}), expected={expected_mA:.04f}mA, calculated={calculated_mA:.04f}mA, error={err*100:.02f}%")
            _pass += 1
    
    print("fail: ", _fail)
    print("pass: ", _pass)
def main():
    import sys
    args = sys.argv[1:]

    m = args[0].lower()

    if m == "v":
        verify(range(0, 256), range(0, 256), [0])
    elif m == "c":
        print(calculate_current([int(args[1]), int(args[2]), int(args[3])]))


if __name__ == "__main__":
    main()