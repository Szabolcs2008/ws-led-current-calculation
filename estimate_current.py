from colorama import Fore
import colorama
colorama.init(autoreset=True)


MA_PER_LED = 10
MA_IDLE = 0.5

# Technically PHASE_SHIFT_* are not really needed and can be
# hardcoded, but different chips probably have different behaviour
PHASE_SHIFT_R = 0
PHASE_SHIFT_G = 63
PHASE_SHIFT_B = 127


PRINT = 0

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
    # This probably can be further optimized (in c++), but I'm not 
    # sure about it's actual performance, as I have not tested it yet in WLED

    if rgb == (0, 0, 0):
        return MA_IDLE
    
    r, g, b = rgb

    # Start by adding everything together
    val = r+g+b

    if PRINT: print("bri", val)

    # Then remove intersections 
    if g and r:
        # this was the original idea
        # g_start = PHASE_SHIFT_G
        # g_end = (PHASE_SHIFT_G + g) % 256
        # r_start = 0
        # r_end = r

        # g_i = min(g_end, r_end) - g_start if r > 64 else 0
        # if g > 192:
        #     g_i = g_i + r

        # val -= g_i

        # It can be "optimized" into this 
        gr_i = (min((PHASE_SHIFT_G + g) % 256, r) - PHASE_SHIFT_G) if r > 64 else 0
#                                                                         ^^ (PHASE_SHIFT_G + 1)
        if g > 192: gr_i += r
#              ^^^ (255 - (PHASE_SHIFT_G - PHASE_SHIFT_R)) = 255 - (63 - 0)
        val -= gr_i
        if PRINT: print("rg", gr_i)
    
    if g and b:
        # Same as above, but with different values, and normalized to start at 0
        g_end = (PHASE_SHIFT_G + g - 64) % 256
        b_start = PHASE_SHIFT_B - 64
        b_end = (PHASE_SHIFT_B + b - 64) % 256

        gb_i = min(b_end, g_end) - b_start if g > 64 else 0
        if b > 192:
            gb_i = gb_i + g

        val -= gb_i
        if PRINT: print("gb", gb_i)
    
    if r and b:
        # Again, same as the above but with different values
        r_end = r
        b_start = PHASE_SHIFT_B
        b_end = (PHASE_SHIFT_B + b) % 256

        rb_i = min(r_end, b_end) - b_start if r > 128 else 0
        if b > 128:
            rb_i = rb_i + r

        val -= rb_i
        if PRINT: print("rb", rb_i)
    
    # I could not come up with anything that could determine the 
    # common active time of the 3 channels, so fall back to a less
    # accurate calculation
    # Surprisingly it only cases 35 cases to fail, but all are overestimations
    # Without this only 11 cases fail, but all are extreme underestimations
    # with close to -100% error 
    if r and g and b:
        val = min(r+g+b, 255)
    
    return MA_PER_LED * (val / 255) + MA_IDLE

def verify(r_range=range(0, 256), g_range=range(0, 256), b_range=range(0, 256)):
    # Test my code against the measured data
    # The range arguments were for testing individual components

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
    # run with 'python3 program.py v' to run tests
    # run with 'python3 program.py c R G B' to calculate the current for an RGB value
    import sys
    args = sys.argv[1:]

    m = args[0].lower()

    if m == "v":
        verify()
    elif m == "c":
        print(calculate_current([int(args[1]), int(args[2]), int(args[3])]))


if __name__ == "__main__":
    main()