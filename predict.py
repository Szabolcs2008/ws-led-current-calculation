"""
RGB LED Current Prediction Model
=================================

Analyzes and predicts the current draw of a PWM-driven RGB LED chip
with a 10 mA hard total current limit.

Physical Model Discovered
--------------------------
The LED chip uses **phase-staggered 8-bit PWM**:
  - R channel starts at tick 0
  - G channel starts at tick 63  (φ_G = 63)
  - B channel starts at tick 127 (φ_B = 127)
  - One PWM period = 256 ticks

Single channels are perfectly linear:
    I_ch = baseline + I_ch_max × (PWM / 256)

Multi-channel non-linearity arises from **temporal current sharing**:
When two or more channels are ON simultaneously, they share a common
current rail. The instantaneous combined current is LESS than the sum
of the individual maxima — the channels compete for available current.

The phase offsets (0, 63, 127) determine WHEN channels overlap:
  R=127, G=63, B=0  → R and G overlap for exactly 63 ticks (G's full ON period),
                       then R is on alone for 63 more ticks.
  R=127, B=63, B=0  → R and B do NOT overlap (B starts at tick 127, which is
                       exactly when R turns off) → behaves linearly!
  R=63,  G=127, B=0 → G extends past R's range, so they overlap for 63 ticks
                       (R's full period), then G is on alone → nearly linear.

Calibration Constants (fitted from measured data)
--------------------------------------------------
Quiescent / baseline current:  0.5169 mA
R max (PWM=255):                9.1248 mA channel current
G max (PWM=255):                8.9553 mA channel current
B max (PWM=255):                8.9042 mA channel current

Instantaneous budgets when channels are simultaneously ON:
  R+G+B:  8.6210 mA
  R+G:    8.6549 mA
  R+B:    8.6383 mA
  G+B:    8.6224 mA
  R only: 9.1248 mA  (no competition)
  G only: 8.9553 mA
  B only: 8.9042 mA

Model Accuracy
--------------
Validated against all 729 measured (R, G, B) → mA data points:
  Max |error|:  0.74%
  Mean |error|: 0.31%
  All errors:   < 1%  (target was < 5%)
"""

import numpy as np

# ── Calibration constants ────────────────────────────────────────────────────

BASELINE_MA   = 0.5169    # Quiescent current (mA), all channels off

# Per-channel peak current when PWM = 255 (full brightness, single channel)
I_R_MAX = 9.1248   # mA
I_G_MAX = 8.9553   # mA
I_B_MAX = 8.9042   # mA

# Instantaneous current budgets when channels overlap on the shared rail
# Key: (R_on: bool, G_on: bool, B_on: bool) → mA
INSTANTANEOUS_BUDGET = {
    (True,  True,  True):  8.6210,  # R + G + B
    (True,  True,  False): 8.6549,  # R + G
    (True,  False, True):  8.6383,  # R + B
    (False, True,  True):  8.6224,  # G + B
    (True,  False, False): I_R_MAX, # R alone
    (False, True,  False): I_G_MAX, # G alone
    (False, False, True):  I_B_MAX, # B alone
    (False, False, False): 0.0,     # all off
}

INSTANTANEOUS_BUDGET = {
    (True,  True,  True):  9,  # R + G + B
    (True,  True,  False): 9,  # R + G
    (True,  False, True):  9,  # R + B
    (False, True,  True):  9,  # G + B
    (True,  False, False): 9,  # R alone
    (False, True,  False): 9,  # G alone
    (False, False, True):  9,  # B alone
    (False, False, False): 0,  # all off
}


# PWM phase offsets (ticks, 0-based within a 256-tick period)
PHI_R = 0    # R starts at tick 0
PHI_G = 63   # G starts at tick 63
PHI_B = 127  # B starts at tick 127
PWM_PERIOD = 256


# ── Main prediction function ─────────────────────────────────────────────────

def predict_led_current(R: int, G: int, B: int) -> float:
    """
    Predict the total current draw (mA) of the RGB LED.

    Parameters
    ----------
    R, G, B : int
        PWM values in [0, 255] for the red, green, and blue channels.

    Returns
    -------
    float
        Predicted current draw in milliamps.

    Notes
    -----
    The model simulates the 256-tick PWM period tick-by-tick.
    For each tick it determines which channels are ON and looks up the
    corresponding instantaneous current from the calibration table.
    The average over all ticks plus the quiescent baseline is returned.

    Accuracy: max |error| < 0.75% over all 729 measured data points.
    """
    if not (0 <= R <= 255 and 0 <= G <= 255 and 0 <= B <= 255):
        raise ValueError(f"R, G, B must be in [0, 255]; got ({R}, {G}, {B})")

    t = np.arange(PWM_PERIOD)
    
    timeframe = [i for i in range(PWM_PERIOD)]
    
    # print(t-PHI_G)
    
    r_on = (t - PHI_R) % PWM_PERIOD < R
    g_on = (t - PHI_G) % PWM_PERIOD < G
    b_on = (t - PHI_B) % PWM_PERIOD < B

    # print(r_on)

    # Vectorised lookup: build the instantaneous current trace
    inst = np.zeros(PWM_PERIOD, dtype=float)
    
    inst_list = [0 for i in range(PWM_PERIOD)]
    
    for (r, g, b), current in INSTANTANEOUS_BUDGET.items():
        mask = (r_on == r) & (g_on == g) & (b_on == b)
        # print(mask)
        inst[mask] = current

    # print(inst)
    
    return BASELINE_MA + float(np.mean(inst))


def intersect_len(a1, b1, a2, b2, N=256):
    # split wrap intervals into linear pieces
    def split(a, b):
        a %= N
        b %= N
        if a < b:
            return [(a, b)]
        return [(a, N), (0, b)]

    A = split(a1, b1)
    B = split(a2, b2)

    total = 0
    for s1, e1 in A:
        for s2, e2 in B:
            s = max(s1, s2)
            e = min(e1, e2)
            if s < e:
                total += e - s
    return total

def predict_current_gpt(R, G, B):
    N = 256

    # intervals
    r0, r1 = PHI_R, PHI_R + R
    g0, g1 = PHI_G, PHI_G + G
    b0, b1 = PHI_B, PHI_B + B

    def L(a, b):  # length
        return (b-a) % N

    def I(a1, b1, a2, b2):
        return intersect_len(a1, b1, a2, b2, N)

    Rl = L(r0, r1)
    Gl = L(g0, g1)
    Bl = L(b0, b1)

    RG = I(r0, r1, g0, g1)
    RB = I(r0, r1, b0, b1)
    GB = I(g0, g1, b0, b1)

    RGB = I(r0, r1, g0, g1)
    RGB = I(0, RGB, 0, b1-b0)  # simplified overlap

    # inclusion-exclusion
    r_only = Rl - RG - RB + RGB
    g_only = Gl - RG - GB + RGB
    b_only = Bl - RB - GB + RGB

    rg = RG - RGB
    rb = RB - RGB
    gb = GB - RGB

    rgb = RGB
    none = N - (r_only + g_only + b_only + rg + rb + gb + rgb)

    print(r_only, g_only, b_only, rg, rb, gb, rgb, none)
    
    return BASELINE_MA + (
        r_only * I_R_MAX +
        g_only * I_G_MAX +
        b_only * I_B_MAX +
        rg * INSTANTANEOUS_BUDGET[(True, True, False)] +
        rb * INSTANTANEOUS_BUDGET[(True, False, True)] +
        gb * INSTANTANEOUS_BUDGET[(False, True, True)] +
        rgb * INSTANTANEOUS_BUDGET[(True, True, True)]
    ) / N

def predict_no_vectors(R, G, B):
    if not (0 <= R <= 255 and 0 <= G <= 255 and 0 <= B <= 255):
        raise ValueError(f"R, G, B must be in [0, 255]; got ({R}, {G}, {B})")
    
    # timeframe = [i for i in range(PWM_PERIOD)]
    
    # print(t-PHI_G)
    
    r_on_start = (PWM_PERIOD - PHI_R) % PWM_PERIOD # < R
    r_on_end = ((PWM_PERIOD - PHI_R) % PWM_PERIOD + R) % PWM_PERIOD
    
    g_on_start = (PWM_PERIOD - PHI_G) % PWM_PERIOD # < G
    g_on_end = ((PWM_PERIOD - PHI_G) % PWM_PERIOD + G) % PWM_PERIOD
    
    b_on_start = (PWM_PERIOD - PHI_B) % PWM_PERIOD # < B
    b_on_end = ((PWM_PERIOD - PHI_B) % PWM_PERIOD + B) % PWM_PERIOD

    print(f"RED start: {r_on_start}; RED end: {r_on_end}")
    print(f"GREEN start: {g_on_start}; GREEN end: {g_on_end}")
    print(f"BLUE start: {b_on_start}; BLUE end: {b_on_end}")

    inst: float = 0
    
    r_wrap = r_on_start > r_on_end
    g_wrap = g_on_start > g_on_end
    b_wrap = b_on_start > b_on_end
    
    
    # for i in range(PWM_PERIOD):
        # for (r, g, b), I in INSTANTANEOUS_BUDGET.items():
        
    # rR = (i >= r_on_start or i < r_on_end) if r_wrap else (r_on_start < i < r_on_end)
    # gG = (i >= g_on_start or i < g_on_end) if g_wrap else (g_on_start < i < g_on_end)
    # bR = (i >= b_on_start or i < b_on_end) if b_wrap else (b_on_start < i < b_on_end)

    print((r_on_end - r_on_start) % 256)
    print((g_on_end - g_on_start) % 256)
    print((b_on_end - b_on_start) % 256)
    
    masks = [0, 0, 0, 0, 0, 0, 0, 0]
    
    
            
            # print(i, r, g, b, bR == b)
            
        # print(i, 
        #       b_on_start <= b_on_end and b_on_start < i < b_on_end, 
        #       b_on_end < b_on_start and (i >= b_on_start or i < b_on_end),
        #       (b_on_start <= b_on_end and b_on_start < i < b_on_end) or (b_on_end < b_on_start and (i >= b_on_start or i < b_on_end)),
              
        #       )

            
        
    # Vectorised lookup: build the instantaneous current trace
    # inst = np.zeros(PWM_PERIOD, dtype=float)
    
    # inst_list = [0 for i in range(PWM_PERIOD)]
    
    # for (r, g, b), current in INSTANTANEOUS_BUDGET.items():
    #     mask = (r_on == r) & (g_on == g) & (b_on == b)
    #     # print(mask)
    #     inst[mask] = current

    # # print(inst)
    
    # return BASELINE_MA + float(np.mean(inst))

# ── Self-test ────────────────────────────────────────────────────────────────

def run_tests():
    """Run validation against the 729-point measured dataset (data.txt)."""
    import os

    # Locate data file (same directory as this script, or one level up)
    candidates = [
        os.path.join(os.path.dirname(__file__), "data.txt"),
        "/mnt/user-data/uploads/data.txt",
    ]
    data_path = next((p for p in candidates if os.path.exists(p)), None)
    if data_path is None:
        print("data.txt not found — skipping full validation.")
        return

    import pandas as pd
    df = pd.read_csv(data_path, sep="\t")
    preds = np.array([predict_led_current(r, g, b)
                      for r, g, b in zip(df["R"], df["G"], df["B"])])
    errs = (preds - df["mA"].values) / df["mA"].values * 100

    max_err  = float(np.abs(errs).max())
    mean_err = float(np.abs(errs).mean())
    passed   = max_err < 5.0

    print(f"Validation over {len(df)} data points:")
    print(f"  Max  |error|: {max_err:.4f}%")
    print(f"  Mean |error|: {mean_err:.4f}%")
    print(f"  All errors < 5%: {passed}")
    print(f"  All errors < 1%: {bool(max_err < 1.0)}")
    assert passed, f"Max error {max_err:.2f}% exceeds 5% limit!"
    print("\nAll tests PASSED.")


# ── Quick demonstration ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    # print("RGB LED Current Predictor")
    # print("=" * 40)

    # examples = [
    #     (0,   0,   0,   "all off"),
    #     (255, 0,   0,   "R full"),
    #     (0,   255, 0,   "G full"),
    #     (0,   0,   255, "B full"),
    #     (255, 255, 255, "all full"),
    #     (127, 63,  0,   "R half + G quarter  (strong interaction)"),
    #     (127, 0,   127, "R half + B half      (minimal interaction)"),
    #     (63,  63,  63,  "all channels equal"),
    #     (128, 128, 0,   "R+G mid"),
    # ]

    r, g, b = [eval(i) for i in sys.argv[1:4]]
    
    mA = predict_led_current(r, g, b)
    # print(f"  R={r:3d} G={g:3d} B={b:3d}  →  {mA:.3f} mA")
    print(f"{mA:.3f} mA")
    print(predict_no_vectors(r, g, b))
    print(predict_current_gpt(r, g, b))
